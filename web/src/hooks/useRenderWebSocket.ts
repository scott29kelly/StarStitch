/**
 * WebSocket hook for real-time render progress updates.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import type { RenderProgress, JobState } from '../api/client';

/**
 * WebSocket message types
 */
export type WebSocketMessageType = 
  | 'state'
  | 'progress'
  | 'complete'
  | 'error'
  | 'cancelled'
  | 'heartbeat'
  | 'pong';

/**
 * WebSocket message
 */
export interface WebSocketMessage {
  type: WebSocketMessageType;
  job_id: string;
  data: Record<string, unknown>;
  timestamp: string;
}

/**
 * WebSocket connection state
 */
export type ConnectionState = 'connecting' | 'connected' | 'disconnected' | 'error';

/**
 * Render progress from WebSocket
 */
export interface RenderProgressState {
  state: JobState;
  progress?: RenderProgress;
  outputPath?: string;
  variantPaths?: Record<string, string>;
  errorMessage?: string;
}

/**
 * Hook return type
 */
export interface UseRenderWebSocketReturn {
  connectionState: ConnectionState;
  renderState: RenderProgressState | null;
  connect: (wsUrl: string) => void;
  disconnect: () => void;
  cancel: () => void;
}

/**
 * Hook for subscribing to render progress via WebSocket.
 * 
 * @param onComplete - Callback when render completes
 * @param onError - Callback when render fails
 */
export function useRenderWebSocket(
  onComplete?: (outputPath: string, variantPaths: Record<string, string>) => void,
  onError?: (error: string) => void,
): UseRenderWebSocketReturn {
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected');
  const [renderState, setRenderState] = useState<RenderProgressState | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const heartbeatIntervalRef = useRef<number | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const currentUrlRef = useRef<string | null>(null);

  /**
   * Clear all intervals and timeouts
   */
  const clearTimers = useCallback(() => {
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = null;
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  }, []);

  /**
   * Handle incoming WebSocket messages
   */
  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const message: WebSocketMessage = JSON.parse(event.data);
      
      switch (message.type) {
        case 'state':
        case 'progress':
          setRenderState({
            state: (message.data.state as JobState) || 'running',
            progress: message.data.progress as RenderProgress | undefined,
          });
          break;
          
        case 'complete': {
          const outputPath = message.data.output_path as string;
          const variantPaths = (message.data.variant_paths as Record<string, string>) || {};
          setRenderState({
            state: 'complete',
            outputPath,
            variantPaths,
          });
          onComplete?.(outputPath, variantPaths);
          break;
        }
          
        case 'error': {
          const errorMsg = message.data.message as string;
          setRenderState({
            state: 'failed',
            errorMessage: errorMsg,
          });
          onError?.(errorMsg);
          break;
        }
          
        case 'cancelled':
          setRenderState({
            state: 'cancelled',
          });
          break;
          
        case 'heartbeat':
        case 'pong':
          // Heartbeat received, connection is alive
          break;
          
        default:
          console.debug('Unknown WebSocket message type:', message.type);
      }
    } catch (e) {
      console.error('Failed to parse WebSocket message:', e);
    }
  }, [onComplete, onError]);

  /**
   * Internal connection function
   */
  const createConnection = useCallback((wsUrl: string) => {
    // Close existing connection
    if (wsRef.current) {
      wsRef.current.close();
    }
    clearTimers();

    setConnectionState('connecting');
    setRenderState(null);
    currentUrlRef.current = wsUrl;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnectionState('connected');
      
      // Start heartbeat
      heartbeatIntervalRef.current = window.setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }));
        }
      }, 30000); // Every 30 seconds
    };

    ws.onmessage = handleMessage;

    ws.onerror = (event) => {
      console.error('WebSocket error:', event);
      setConnectionState('error');
    };

    ws.onclose = (event) => {
      clearTimers();
      
      if (event.wasClean) {
        setConnectionState('disconnected');
        currentUrlRef.current = null;
      } else {
        setConnectionState('error');
        // Don't auto-reconnect to avoid connection storms
      }
    };
  }, [clearTimers, handleMessage]);

  /**
   * Connect to WebSocket
   */
  const connect = useCallback((wsUrl: string) => {
    createConnection(wsUrl);
  }, [createConnection]);

  /**
   * Disconnect from WebSocket
   */
  const disconnect = useCallback(() => {
    clearTimers();
    currentUrlRef.current = null;
    
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    
    setConnectionState('disconnected');
  }, [clearTimers]);

  /**
   * Request job cancellation
   */
  const cancel = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'cancel' }));
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      clearTimers();
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [clearTimers]);

  return {
    connectionState,
    renderState,
    connect,
    disconnect,
    cancel,
  };
}
