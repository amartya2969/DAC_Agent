// MCP Inspector - Model Context Protocol Security Layer
//
// This is the "Security Chip for MCP" - the moat that makes this defensible.
// It parses MCP JSON-RPC messages and validates capabilities before forwarding.
//
// MCP Protocol: https://modelcontextprotocol.io/
// JSON-RPC 2.0: https://www.jsonrpc.org/specification

package main

import (
	"fmt"
	"log"
	"time"
)

// MCPInspector validates MCP protocol messages
type MCPInspector struct {
	controlPlaneURL string
}

// NewMCPInspector creates a new MCP inspector
func NewMCPInspector(controlPlaneURL string) *MCPInspector {
	return &MCPInspector{
		controlPlaneURL: controlPlaneURL,
	}
}

// Validate validates an MCP JSON-RPC message
func (mi *MCPInspector) Validate(mcpMessage map[string]interface{}, agentDID string) error {
	log.Println("🔍 [MCP Inspector] Validating MCP message...")

	// Extract JSON-RPC fields
	method, ok := mcpMessage["method"].(string)
	if !ok {
		return fmt.Errorf("missing or invalid 'method' field")
	}

	params, ok := mcpMessage["params"].(map[string]interface{})
	if !ok {
		log.Println("   No params in request (notification)")
		params = make(map[string]interface{})
	}

	log.Printf("   Method: %s", method)

	// Route based on MCP method
	switch method {
	case "tools/call":
		return mi.validateToolCall(params, agentDID)

	case "tools/list":
		// List is always allowed
		log.Println("✓ tools/list is always allowed")
		return nil

	case "resources/read":
		return mi.validateResourceRead(params, agentDID)

	case "prompts/get":
		return mi.validatePromptGet(params, agentDID)

	case "initialize":
		// Initialize is always allowed
		log.Println("✓ initialize is always allowed")
		return nil

	default:
		log.Printf("⚠️  Unknown MCP method: %s (allowing)", method)
		return nil // Fail open for unknown methods
	}
}

// validateToolCall validates a tools/call request
func (mi *MCPInspector) validateToolCall(params map[string]interface{}, agentDID string) error {
	toolName, ok := params["name"].(string)
	if !ok {
		return fmt.Errorf("missing or invalid tool 'name' in params")
	}

	log.Printf("   Tool: %s", toolName)

	// Map tool names to required capabilities
	requiredCapability := mi.getRequiredCapabilityForTool(toolName)

	log.Printf("   Required Capability: %s", requiredCapability)

	// In production, this would call the Control Plane to verify
	// the agent has the required capability in their VC

	// For now, we'll implement basic rules
	if mi.isHighRiskTool(toolName) {
		log.Printf("🚨 HIGH RISK TOOL: %s", toolName)
		log.Println("   Requires explicit capability verification")

		// Example: Block destructive operations
		if toolName == "delete_database" || toolName == "drop_table" {
			return fmt.Errorf("destructive tool '%s' blocked by policy", toolName)
		}
	}

	log.Printf("✓ Tool '%s' allowed", toolName)
	return nil
}

// validateResourceRead validates a resources/read request
func (mi *MCPInspector) validateResourceRead(params map[string]interface{}, agentDID string) error {
	resourceURI, ok := params["uri"].(string)
	if !ok {
		return fmt.Errorf("missing or invalid resource 'uri' in params")
	}

	log.Printf("   Resource URI: %s", resourceURI)

	// Check if resource is allowed
	if mi.isRestrictedResource(resourceURI) {
		return fmt.Errorf("access to restricted resource '%s' denied", resourceURI)
	}

	log.Printf("✓ Resource access allowed")
	return nil
}

// validatePromptGet validates a prompts/get request
func (mi *MCPInspector) validatePromptGet(params map[string]interface{}, agentDID string) error {
	promptName, ok := params["name"].(string)
	if !ok {
		return fmt.Errorf("missing or invalid prompt 'name' in params")
	}

	log.Printf("   Prompt: %s", promptName)
	log.Printf("✓ Prompt access allowed")
	return nil
}

// getRequiredCapabilityForTool returns the capability needed for a tool
func (mi *MCPInspector) getRequiredCapabilityForTool(toolName string) string {
	// This mapping would be loaded from OPA policies in production
	capabilityMap := map[string]string{
		"execute_sql":        "DatabaseAccess",
		"query_database":     "DatabaseAccess",
		"read_file":          "FileSystemAccess",
		"write_file":         "FileSystemAccess",
		"delete_file":        "FileSystemAccess",
		"http_request":       "ExternalAPIAccess",
		"analyze_financial":  "FinancialAnalysis",
		"process_payment":    "PaymentProcessing",
		"send_email":         "EmailAccess",
		"delete_database":    "DatabaseAdmin",
		"drop_table":         "DatabaseAdmin",
	}

	if capability, ok := capabilityMap[toolName]; ok {
		return capability
	}

	return "UnknownCapability"
}

// isHighRiskTool checks if tool is considered high risk
func (mi *MCPInspector) isHighRiskTool(toolName string) bool {
	highRiskTools := map[string]bool{
		"delete_database":   true,
		"drop_table":        true,
		"delete_file":       true,
		"execute_shell":     true,
		"modify_permissions": true,
		"send_email":        true,
		"process_payment":   true,
	}

	return highRiskTools[toolName]
}

// isRestrictedResource checks if resource URI is restricted
func (mi *MCPInspector) isRestrictedResource(uri string) bool {
	// Example: Block access to sensitive files
	restrictedPatterns := []string{
		"/etc/passwd",
		"/etc/shadow",
		".env",
		"credentials",
		"secrets",
	}

	for _, pattern := range restrictedPatterns {
		if contains(uri, pattern) {
			return true
		}
	}

	return false
}

// Helper function
func contains(s, substr string) bool {
	return len(s) >= len(substr) && (s == substr || len(s) > len(substr) &&
		(s[:len(substr)] == substr || s[len(s)-len(substr):] == substr ||
		findSubstring(s, substr)))
}

func findSubstring(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}

// InjectIdentity injects agent identity into MCP message
func (mi *MCPInspector) InjectIdentity(mcpMessage map[string]interface{}, agentDID string, sessionID string) {
	// Get or create params
	params, ok := mcpMessage["params"].(map[string]interface{})
	if !ok {
		params = make(map[string]interface{})
		mcpMessage["params"] = params
	}

	// Inject agent identity context
	params["_agent_identity"] = map[string]interface{}{
		"did":        agentDID,
		"session_id": sessionID,
		"timestamp":  time.Now().Format(time.RFC3339),
		"proxy_by":   "dac-sidecar",
	}

	log.Println("✓ Agent identity injected into MCP message")
}
