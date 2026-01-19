/**
 * WebSocket hook for real-time progress streaming
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { apiClient } from '../api/client';
import type { ProgressEvent } from '../types';

export type WebSocketStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

export interface UseWebSocketOptions {
  /** Auto-reconnect on disconnect */
  autoReconnect?: boolean;
  /** Reconnect delay in ms */
  reconnectDelay?: number;
  /** Maximum reconnect attempts */
  maxReconnectAttempts?: number;
  /** Callback when event is received */
  onEvent?: (event: ProgressEvent) => void;
  /** Callback when connection status changes */
  onStatusChange?: (status: WebSocketStatus) => void;
}

export interface UseWebSocketResult {
  /** Current connection status */
  status: WebSocketStatus;
  /** Last received event */
  lastEvent: ProgressEvent | null;
  /** All received events */
  events: ProgressEvent[];
  /** Connect to WebSocket */
  connect: () => void;
  /** Disconnect from WebSocket */
  disconnect: () => void;
  /** Send a message to the server */
  send: (message: string) => void;
  /** Cancel the job via WebSocket */
  cancelJob: () => void;
}

/**
 * Hook for managing WebSocket connection for render progress
 */
export function useWebSocket(
  jobId: string | null,
  options: UseWebSocketOptions = {}
): UseWebSocketResult {
  const {
    autoReconnect = true,
    reconnectDelay = 3000,
    maxReconnectAttempts = 5,
    onEvent,
    onStatusChange,
  } = options;

  const [status, setStatus] = useState<WebSocketStatus>('disconnected');
  const [lastEvent, setLastEvent] = useState<ProgressEvent | null>(null);
  const [events, setEvents] = useState<ProgressEvent[]>([]);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Update status and trigger callback
  const updateStatus = useCallback(
    (newStatus: WebSocketStatus) => {
      setStatus(newStatus);
      onStatusChange?.(newStatus);
    },
    [onStatusChange]
  );

  // Handle incoming message
  const handleMessage = useCallback(
    (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data) as ProgressEvent;
        setLastEvent(data);
        setEvents((prev) => [...prev, data]);
        onEvent?.(data);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    },
    [onEvent]
  );

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (!jobId) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    // Close existing connection
    if (wsRef.current) {
      wsRef.current.close();
    }

    updateStatus('connecting');

    const url = apiClient.getWebSocketUrl(`/ws/progress/${jobId}`);
    const ws = new WebSocket(url);

    ws.onopen = () => {
      updateStatus('connected');
      reconnectAttemptsRef.current = 0;
    };

    ws.onmessage = handleMessage;

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      updateStatus('error');
    };

    ws.onclose = () => {
      updateStatus('disconnected');

      // Auto-reconnect logic
      if (autoReconnect && reconnectAttemptsRef.current < maxReconnectAttempts) {
        reconnectAttemptsRef.current += 1;
        console.log(
          `WebSocket closed, reconnecting (attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts})...`
        );

        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, reconnectDelay);
      }
    };

    wsRef.current = ws;
  }, [jobId, autoReconnect, reconnectDelay, maxReconnectAttempts, updateStatus, handleMessage]);

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    reconnectAttemptsRef.current = maxReconnectAttempts; // Prevent auto-reconnect

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    updateStatus('disconnected');
  }, [maxReconnectAttempts, updateStatus]);

  // Send a message to the server
  const send = useCallback((message: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(message);
    } else {
      console.warn('WebSocket is not connected');
    }
  }, []);

  // Cancel the job via WebSocket
  const cancelJob = useCallback(() => {
    send('cancel');
  }, [send]);

  // Auto-connect when jobId changes
  useEffect(() => {
    if (jobId) {
      // Reset state for new job
      setEvents([]);
      setLastEvent(null);
      reconnectAttemptsRef.current = 0;
      connect();
    }

    return () => {
      disconnect();
    };
  }, [jobId, connect, disconnect]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return {
    status,
    lastEvent,
    events,
    connect,
    disconnect,
    send,
    cancelJob,
  };
}

export default useWebSocket;
