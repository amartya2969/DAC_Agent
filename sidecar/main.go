// DAC Sidecar - The "Bouncer" for Agent Traffic
//
// This is a transparent HTTP/HTTPS proxy that:
// 1. Intercepts ALL outbound traffic from agent containers
// 2. Calls Control Plane to get user-scoped AWS credentials
// 3. Injects credentials into Authorization header
// 4. Enforces circuit breaking (velocity limits via Redis)
// 5. Inspects MCP protocol messages for capability validation
//
// Deployment: Kubernetes DaemonSet or Docker Sidecar Container

package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/go-redis/redis/v8"
)

// Configuration from environment variables
type Config struct {
	ProxyPort          string
	ControlPlaneURL    string
	RedisURL           string
	PolicyLimitMBPerMin int
	AgentDID           string
}

// Sidecar represents the proxy server
type Sidecar struct {
	config         Config
	redisClient    *redis.Client
	httpClient     *http.Client
	circuitBreaker *CircuitBreaker
	mcpInspector   *MCPInspector
}

// Main entry point
func main() {
	log.Println("🚀 DAC Sidecar starting...")

	// Load configuration
	config := Config{
		ProxyPort:          getEnv("PROXY_PORT", "8080"),
		ControlPlaneURL:    getEnv("CONTROL_PLANE_URL", "http://control-plane:5000"),
		RedisURL:           getEnv("REDIS_URL", "redis:6379"),
		PolicyLimitMBPerMin: getEnvInt("POLICY_LIMIT_MB_PER_MIN", 50),
		AgentDID:           getEnv("AGENT_DID", "did:key:unknown"),
	}

	log.Printf("Configuration:")
	log.Printf("  Proxy Port: %s", config.ProxyPort)
	log.Printf("  Control Plane: %s", config.ControlPlaneURL)
	log.Printf("  Redis: %s", config.RedisURL)
	log.Printf("  Rate Limit: %d MB/min", config.PolicyLimitMBPerMin)

	// Initialize Redis client
	redisClient := redis.NewClient(&redis.Options{
		Addr: config.RedisURL,
		Password: "",
		DB: 0,
	})

	// Test Redis connection
	ctx := context.Background()
	if err := redisClient.Ping(ctx).Err(); err != nil {
		log.Printf("⚠️  Warning: Redis not available: %v", err)
		log.Println("   Circuit breaker will operate in memory-only mode")
	} else {
		log.Println("✓ Connected to Redis")
	}

	// Create sidecar instance
	sidecar := &Sidecar{
		config:      config,
		redisClient: redisClient,
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
		circuitBreaker: NewCircuitBreaker(redisClient, config.AgentDID, config.PolicyLimitMBPerMin),
		mcpInspector:   NewMCPInspector(config.ControlPlaneURL),
	}

	// Create HTTP server
	http.HandleFunc("/", sidecar.proxyHandler)
	http.HandleFunc("/health", sidecar.healthHandler)
	http.HandleFunc("/metrics", sidecar.metricsHandler)

	addr := ":" + config.ProxyPort
	log.Printf("\n✅ DAC Sidecar listening on %s", addr)
	log.Println("   All agent traffic will be intercepted and validated")
	log.Println("")

	if err := http.ListenAndServe(addr, nil); err != nil {
		log.Fatal(err)
	}
}

// proxyHandler is the main request handler
func (s *Sidecar) proxyHandler(w http.ResponseWriter, r *http.Request) {
	startTime := time.Now()

	log.Printf("\n📥 Incoming Request:")
	log.Printf("   Method: %s", r.Method)
	log.Printf("   URL: %s", r.URL.String())
	log.Printf("   Agent: %s", s.config.AgentDID[:40]+"...")

	// STEP 1: Check Circuit Breaker (Pre-Flight)
	allowed, reason := s.circuitBreaker.CheckLimit(r.Context())
	if !allowed {
		log.Printf("🚫 Circuit Breaker: Request BLOCKED")
		log.Printf("   Reason: %s", reason)
		http.Error(w, fmt.Sprintf("Circuit Breaker: %s", reason), http.StatusTooManyRequests)
		return
	}

	// STEP 2: Check if this is an MCP request
	if s.isMCPRequest(r) {
		log.Println("🛡️  MCP Request detected - inspecting...")
		if err := s.handleMCPRequest(w, r); err != nil {
			log.Printf("❌ MCP Validation failed: %v", err)
			return
		}
	}

	// STEP 3: Get credentials from Control Plane
	credentials, err := s.getCredentialsFromControlPlane(r.Context())
	if err != nil {
		log.Printf("❌ Failed to get credentials: %v", err)
		http.Error(w, "Authentication failed", http.StatusUnauthorized)
		return
	}

	// STEP 4: Inject credentials into request
	r.Header.Set("Authorization", credentials)
	r.Header.Set("X-Agent-DID", s.config.AgentDID)
	r.Header.Set("X-Proxy-By", "DAC-Sidecar")

	// STEP 5: Forward request to target
	targetURL := r.URL.String()
	if !strings.HasPrefix(targetURL, "http") {
		targetURL = "https://" + r.Host + targetURL
	}

	proxyReq, err := http.NewRequest(r.Method, targetURL, r.Body)
	if err != nil {
		log.Printf("❌ Failed to create proxy request: %v", err)
		http.Error(w, "Proxy error", http.StatusInternalServerError)
		return
	}

	// Copy headers
	proxyReq.Header = r.Header

	log.Printf("📤 Forwarding to: %s", targetURL)

	// Execute request
	resp, err := s.httpClient.Do(proxyReq)
	if err != nil {
		log.Printf("❌ Proxy request failed: %v", err)
		http.Error(w, "Upstream error", http.StatusBadGateway)
		return
	}
	defer resp.Body.Close()

	// STEP 6: Read response and track usage
	bodyBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		log.Printf("❌ Failed to read response: %v", err)
		http.Error(w, "Response read error", http.StatusInternalServerError)
		return
	}

	responseSize := len(bodyBytes)

	// STEP 7: Update Circuit Breaker (Post-Flight)
	s.circuitBreaker.RecordUsage(r.Context(), responseSize)

	// STEP 8: Check if response exceeds limit
	if responseSize > s.config.PolicyLimitMBPerMin*1024*1024 {
		log.Printf("🚫 Circuit Breaker: Response TOO LARGE (%d bytes)", responseSize)
		log.Println("   Killing connection immediately")
		http.Error(w, "Response size limit exceeded", http.StatusPayloadTooLarge)
		return
	}

	// STEP 9: Forward response to agent
	for k, v := range resp.Header {
		w.Header()[k] = v
	}
	w.WriteHeader(resp.StatusCode)
	w.Write(bodyBytes)

	duration := time.Since(startTime)
	log.Printf("✅ Request completed in %v", duration)
	log.Printf("   Response: %d bytes (Status: %d)", responseSize, resp.StatusCode)
}

// getCredentialsFromControlPlane calls the control plane to get AWS credentials
func (s *Sidecar) getCredentialsFromControlPlane(ctx context.Context) (string, error) {
	// Call control plane API to exchange VC for AWS token
	url := s.config.ControlPlaneURL + "/api/exchange-credential"

	reqBody := map[string]interface{}{
		"agent_did": s.config.AgentDID,
	}

	jsonBody, _ := json.Marshal(reqBody)
	req, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewBuffer(jsonBody))
	if err != nil {
		return "", err
	}

	req.Header.Set("Content-Type", "application/json")

	resp, err := s.httpClient.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("control plane returned status %d", resp.StatusCode)
	}

	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return "", err
	}

	// Extract AWS credentials and format as Authorization header
	accessKey := result["AccessKeyId"].(string)
	secretKey := result["SecretAccessKey"].(string)
	sessionToken := result["SessionToken"].(string)

	// For demonstration, return a bearer token format
	// In production, this would be AWS SigV4 signature
	credentials := fmt.Sprintf("Bearer %s:%s:%s", accessKey, secretKey, sessionToken)

	return credentials, nil
}

// isMCPRequest checks if request is MCP protocol
func (s *Sidecar) isMCPRequest(r *http.Request) bool {
	// MCP uses JSON-RPC over HTTP POST
	return r.Method == "POST" &&
		strings.Contains(r.URL.Path, "/mcp") &&
		strings.Contains(r.Header.Get("Content-Type"), "application/json")
}

// handleMCPRequest processes MCP-specific validation
func (s *Sidecar) handleMCPRequest(w http.ResponseWriter, r *http.Request) error {
	// Read body
	bodyBytes, err := io.ReadAll(r.Body)
	if err != nil {
		return err
	}

	// Restore body for downstream
	r.Body = io.NopCloser(bytes.NewBuffer(bodyBytes))

	// Parse MCP message
	var mcpMsg map[string]interface{}
	if err := json.Unmarshal(bodyBytes, &mcpMsg); err != nil {
		return fmt.Errorf("invalid MCP message: %w", err)
	}

	// Validate with MCP inspector
	return s.mcpInspector.Validate(mcpMsg, s.config.AgentDID)
}

// healthHandler provides health check endpoint
func (s *Sidecar) healthHandler(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]string{
		"status": "healthy",
		"service": "dac-sidecar",
	})
}

// metricsHandler provides Prometheus-style metrics
func (s *Sidecar) metricsHandler(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	usage, _ := s.circuitBreaker.GetCurrentUsage(ctx)

	w.Header().Set("Content-Type", "text/plain")
	fmt.Fprintf(w, "# HELP dac_agent_bytes_used Total bytes used by agent\n")
	fmt.Fprintf(w, "# TYPE dac_agent_bytes_used gauge\n")
	fmt.Fprintf(w, "dac_agent_bytes_used{agent_did=\"%s\"} %d\n", s.config.AgentDID, usage)
}

// Utility functions
func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func getEnvInt(key string, defaultValue int) int {
	if value := os.Getenv(key); value != "" {
		if i, err := strconv.Atoi(value); err == nil {
			return i
		}
	}
	return defaultValue
}
