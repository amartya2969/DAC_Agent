// Package main - Audit logging for Identity-First Observability
//
// This provides structured JSON logging to stdout that shows:
// - WHO made the request (user attribution)
// - WHAT they tried to access (intent detection)
// - RESULT (allowed or blocked)
//
// Usage: docker logs -f sidecar | jq
//
// This IS the observability layer - logs are the byproduct of enforcement.

package main

import (
	"encoding/json"
	"os"
	"time"
)

// AuditLog represents a single request event with complete attribution
type AuditLog struct {
	Timestamp string `json:"ts"`              // RFC3339 timestamp
	Event     string `json:"event"`           // "TRAFFIC", "SECURITY_ALERT", "CIRCUIT_BREAK"
	User      string `json:"user"`            // Extracted user ID (from session/VC)
	Target    string `json:"target"`          // Target resource (e.g., "s3", "database")
	Intent    string `json:"intent"`          // What they're trying to do
	Outcome   string `json:"outcome"`         // "ALLOWED", "BLOCKED", "REVOKED"
	Reason    string `json:"reason,omitempty"` // Why it was blocked (if applicable)
	Session   string `json:"session,omitempty"` // Session UUID for correlation
	BytesSent int64  `json:"bytes_sent,omitempty"` // For circuit breaker tracking
}

// LogTraffic logs a normal traffic event (allowed request)
func LogTraffic(user, target, intent, session string, bytesSent int64) {
	entry := AuditLog{
		Timestamp: time.Now().Format(time.RFC3339),
		Event:     "TRAFFIC",
		User:      user,
		Target:    target,
		Intent:    intent,
		Outcome:   "ALLOWED",
		Session:   session,
		BytesSent: bytesSent,
	}
	json.NewEncoder(os.Stdout).Encode(entry)
}

// LogBlocked logs a blocked request (security enforcement)
func LogBlocked(user, target, intent, reason, session string) {
	entry := AuditLog{
		Timestamp: time.Now().Format(time.RFC3339),
		Event:     "SECURITY_ALERT",
		User:      user,
		Target:    target,
		Intent:    intent,
		Outcome:   "BLOCKED",
		Reason:    reason,
		Session:   session,
	}
	json.NewEncoder(os.Stdout).Encode(entry)
}

// LogCircuitBreak logs a circuit breaker event
func LogCircuitBreak(user, reason, session string, bytesUsed int64) {
	entry := AuditLog{
		Timestamp: time.Now().Format(time.RFC3339),
		Event:     "CIRCUIT_BREAK",
		User:      user,
		Target:    "circuit-breaker",
		Intent:    "rate-limit-enforcement",
		Outcome:   "BLOCKED",
		Reason:    reason,
		Session:   session,
		BytesSent: bytesUsed,
	}
	json.NewEncoder(os.Stdout).Encode(entry)
}

// LogRevocation logs a session revocation event
func LogRevocation(user, session, reason string) {
	entry := AuditLog{
		Timestamp: time.Now().Format(time.RFC3339),
		Event:     "SECURITY_ALERT",
		User:      user,
		Target:    "session-authority",
		Intent:    "session-revocation",
		Outcome:   "REVOKED",
		Reason:    reason,
		Session:   session,
	}
	json.NewEncoder(os.Stdout).Encode(entry)
}

// detectIntent extracts intent from request method and path
func detectIntent(method, path string) string {
	// Simple intent detection based on HTTP method and path patterns
	switch method {
	case "GET":
		return "READ " + path
	case "POST":
		return "CREATE " + path
	case "PUT":
		return "UPDATE " + path
	case "DELETE":
		return "DELETE " + path
	default:
		return method + " " + path
	}
}

// extractTarget extracts target service from host or path
func extractTarget(host, path string) string {
	// Simple target extraction - in production would be more sophisticated
	if host != "" {
		return host
	}
	if len(path) > 0 && path[0] == '/' {
		parts := []rune(path)
		for i, r := range parts[1:] {
			if r == '/' {
				return string(parts[1 : i+1])
			}
		}
	}
	return "unknown"
}
