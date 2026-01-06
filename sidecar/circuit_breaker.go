// Circuit Breaker - Redis-backed Velocity Limits
//
// This implements the "Kill Switch" logic:
// - Track bytes/requests per agent per minute
// - If limit exceeded, return 429 (Too Many Requests)
// - If single response > limit, kill TCP connection immediately

package main

import (
	"context"
	"fmt"
	"log"
	"time"

	"github.com/go-redis/redis/v8"
)

// CircuitBreaker manages rate limiting for agents
type CircuitBreaker struct {
	redisClient *redis.Client
	agentDID    string
	limitMBPerMin int
	windowSeconds int
}

// NewCircuitBreaker creates a new circuit breaker
func NewCircuitBreaker(redisClient *redis.Client, agentDID string, limitMBPerMin int) *CircuitBreaker {
	return &CircuitBreaker{
		redisClient:   redisClient,
		agentDID:      agentDID,
		limitMBPerMin: limitMBPerMin,
		windowSeconds: 60, // 1 minute window
	}
}

// CheckLimit checks if agent is within rate limit (pre-flight check)
func (cb *CircuitBreaker) CheckLimit(ctx context.Context) (bool, string) {
	usage, err := cb.GetCurrentUsage(ctx)
	if err != nil {
		log.Printf("⚠️  Circuit breaker error: %v (allowing request)", err)
		return true, "" // Fail open
	}

	limitBytes := cb.limitMBPerMin * 1024 * 1024

	if usage >= int64(limitBytes) {
		reason := fmt.Sprintf("Rate limit exceeded: %d MB used of %d MB allowed per minute",
			usage/(1024*1024), cb.limitMBPerMin)
		return false, reason
	}

	remaining := int64(limitBytes) - usage
	log.Printf("✓ Circuit Breaker: OK (%d MB remaining)", remaining/(1024*1024))

	return true, ""
}

// RecordUsage records bytes used by the agent (post-flight)
func (cb *CircuitBreaker) RecordUsage(ctx context.Context, bytes int) {
	key := cb.getRedisKey()

	// Increment usage counter
	pipe := cb.redisClient.Pipeline()
	pipe.IncrBy(ctx, key, int64(bytes))
	pipe.Expire(ctx, key, time.Duration(cb.windowSeconds)*time.Second)

	if _, err := pipe.Exec(ctx); err != nil {
		log.Printf("⚠️  Failed to record usage: %v", err)
		return
	}

	log.Printf("📊 Recorded %d bytes usage for agent", bytes)
}

// GetCurrentUsage returns current usage in bytes
func (cb *CircuitBreaker) GetCurrentUsage(ctx context.Context) (int64, error) {
	key := cb.getRedisKey()

	val, err := cb.redisClient.Get(ctx, key).Int64()
	if err == redis.Nil {
		return 0, nil // No usage yet
	}
	if err != nil {
		return 0, err
	}

	return val, nil
}

// ResetUsage resets the usage counter (for testing/admin)
func (cb *CircuitBreaker) ResetUsage(ctx context.Context) error {
	key := cb.getRedisKey()
	return cb.redisClient.Del(ctx, key).Err()
}

// getRedisKey generates the Redis key for this agent's usage
func (cb *CircuitBreaker) getRedisKey() string {
	// Format: usage:<agent_did>:<window_start>
	// Window start is rounded to nearest minute
	windowStart := time.Now().Unix() / int64(cb.windowSeconds) * int64(cb.windowSeconds)
	return fmt.Sprintf("usage:%s:%d", cb.agentDID, windowStart)
}

// GetStats returns circuit breaker statistics
func (cb *CircuitBreaker) GetStats(ctx context.Context) map[string]interface{} {
	usage, _ := cb.GetCurrentUsage(ctx)
	limitBytes := int64(cb.limitMBPerMin * 1024 * 1024)

	return map[string]interface{}{
		"agent_did":      cb.agentDID,
		"current_usage_bytes": usage,
		"current_usage_mb":    usage / (1024 * 1024),
		"limit_mb":            cb.limitMBPerMin,
		"remaining_bytes":     limitBytes - usage,
		"remaining_mb":        (limitBytes - usage) / (1024 * 1024),
		"percentage_used":     float64(usage) / float64(limitBytes) * 100,
		"window_seconds":      cb.windowSeconds,
	}
}
