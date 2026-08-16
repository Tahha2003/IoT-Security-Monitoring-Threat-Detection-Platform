import React, { useState, useEffect, useCallback, useRef } from "react";

const SEV_STYLE = {
  CRITICAL: {
    bg: "linear-gradient(135deg, #1a0000 0%, #2d0000 100%)",
    border: "#ff2d2d",
    accent: "#ff2d2d",
    glow: "0 0 24px #ff2d2d66, 0 4px 20px #00000099",
    icon: "🚨",
    label: "CRITICAL THREAT",
  },
  HIGH: {
    bg: "linear-gradient(135deg, #1a0800 0%, #2d1200 100%)",
    border: "#ff6b00",
    accent: "#ff6b00",
    glow: "0 0 20px #ff6b0055, 0 4px 20px #00000099",
    icon: "⚠️",
    label: "HIGH SEVERITY",
  },
};

function QuarantineDialog({ alert, onQuarantine, onIgnore }) {
  const [confirming, setConfirming] = useState(false);
  const [countdown, setCountdown] = useState(10);

  useEffect(() => {
    if (!confirming) return;
    if (countdown <= 0) { onIgnore(); return; }
    const t = setTimeout(() => setCountdown(c => c - 1), 1000);
    return () => clearTimeout(t);
  }, [confirming, countdown, onIgnore]);

  const sev = SEV_STYLE[alert.severity] || SEV_STYLE.HIGH;

  return (
    <div style={{
      position: "fixed", inset: 0,
      background: "rgba(0,0,0,0.75)",
      backdropFilter: "blur(4px)",
      display: "flex", alignItems: "center", justifyContent: "center",
      zIndex: 9999,
      animation: "dialogFadeIn 0.2s ease",
    }}>
      <div style={{
        background: "#0d0d1e",
        border: `1px solid ${sev.border}`,
        borderRadius: 14,
        padding: "28px 32px",
        width: 460,
        boxShadow: sev.glow,
        animation: "dialogSlideIn 0.25s cubic-bezier(0.34,1.56,0.64,1)",
      }}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20 }}>
          <div style={{
            width: 44, height: 44, borderRadius: 10,
            background: `${sev.border}22`,
            border: `1px solid ${sev.border}`,
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 22,
            boxShadow: `0 0 12px ${sev.border}44`,
          }}>
            {sev.icon}
          </div>
          <div>
            <div style={{ color: sev.accent, fontWeight: 800, fontSize: 13, letterSpacing: 2 }}>
              {sev.label} DETECTED
            </div>
            <div style={{ color: "#666", fontSize: 11, marginTop: 2 }}>
              Immediate action required
            </div>
          </div>
        </div>

        {/* Alert Details */}
        <div style={{
          background: "#0a0a18",
          border: "1px solid #1a1a35",
          borderRadius: 8,
          padding: "12px 16px",
          marginBottom: 20,
          fontFamily: "monospace",
        }}>
          {[
            ["Source IP",    alert.src_ip],
            ["Destination",  `${alert.dst_ip}:${alert.dst_port}`],
            ["Attack Type",  alert.attack_type],
            ["Protocol",     alert.protocol?.toUpperCase()],
            ["Risk Score",   `${(alert.risk_score * 100).toFixed(0)}%`],
          ].map(([k, v]) => (
            <div key={k} style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
              <span style={{ color: "#555", fontSize: 11 }}>{k}</span>
              <span style={{ color: "#ddd", fontSize: 11, fontWeight: "bold" }}>{v || "—"}</span>
            </div>
          ))}
        </div>

        {/* Warning text */}
        <div style={{
          color: "#888", fontSize: 12, marginBottom: 22, lineHeight: 1.6,
          borderLeft: `3px solid ${sev.border}`,
          paddingLeft: 12,
        }}>
          Device <span style={{ color: sev.accent, fontWeight: "bold" }}>{alert.src_ip}</span> is
          exhibiting malicious behavior. Quarantining will block all traffic from this device.
        </div>

        {/* Buttons */}
        <div style={{ display: "flex", gap: 10 }}>
          <button
            onClick={onQuarantine}
            style={{
              flex: 1,
              background: `linear-gradient(135deg, ${sev.border}33, ${sev.border}22)`,
              border: `1px solid ${sev.border}`,
              color: sev.accent,
              borderRadius: 8,
              padding: "10px 0",
              fontSize: 12,
              fontWeight: 800,
              letterSpacing: 1.5,
              cursor: "pointer",
              transition: "all 0.2s",
              boxShadow: `0 0 12px ${sev.border}33`,
            }}
            onMouseEnter={e => e.target.style.boxShadow = `0 0 20px ${sev.border}66`}
            onMouseLeave={e => e.target.style.boxShadow = `0 0 12px ${sev.border}33`}
          >
            🔒 QUARANTINE DEVICE
          </button>
          <button
            onClick={onIgnore}
            style={{
              flex: 1,
              background: "transparent",
              border: "1px solid #2a2a45",
              color: "#666",
              borderRadius: 8,
              padding: "10px 0",
              fontSize: 12,
              fontWeight: 600,
              letterSpacing: 1,
              cursor: "pointer",
              transition: "all 0.2s",
            }}
            onMouseEnter={e => { e.target.style.borderColor = "#444"; e.target.style.color = "#999"; }}
            onMouseLeave={e => { e.target.style.borderColor = "#2a2a45"; e.target.style.color = "#666"; }}
          >
            IGNORE
          </button>
        </div>
      </div>

      <style>{`
        @keyframes dialogFadeIn { from { opacity:0 } to { opacity:1 } }
        @keyframes dialogSlideIn { from { opacity:0; transform:scale(0.85) translateY(20px) } to { opacity:1; transform:scale(1) translateY(0) } }
      `}</style>
    </div>
  );
}

function Toast({ toast, onDismiss, onAction }) {
  const [visible, setVisible] = useState(false);
  const [exiting, setExiting] = useState(false);
  const [progress, setProgress] = useState(100);
  const intervalRef = useRef(null);
  const DURATION = 8000;

  useEffect(() => {
    requestAnimationFrame(() => setVisible(true));
    const start = Date.now();
    intervalRef.current = setInterval(() => {
      const elapsed = Date.now() - start;
      const remaining = Math.max(0, 100 - (elapsed / DURATION) * 100);
      setProgress(remaining);
      if (remaining <= 0) dismiss();
    }, 50);
    return () => clearInterval(intervalRef.current);
  }, []);

  const dismiss = useCallback(() => {
    clearInterval(intervalRef.current);
    setExiting(true);
    setTimeout(() => onDismiss(toast.id), 350);
  }, [toast.id, onDismiss]);

  const sev = SEV_STYLE[toast.severity] || SEV_STYLE.HIGH;

  return (
    <div
      style={{
        background: sev.bg,
        border: `1px solid ${sev.border}`,
        borderRadius: 10,
        padding: "14px 16px",
        width: 360,
        boxShadow: sev.glow,
        cursor: "pointer",
        position: "relative",
        overflow: "hidden",
        transform: visible && !exiting ? "translateX(0) scale(1)" : "translateX(100%) scale(0.95)",
        opacity: visible && !exiting ? 1 : 0,
        transition: "transform 0.35s cubic-bezier(0.34,1.56,0.64,1), opacity 0.35s ease",
        marginBottom: 10,
      }}
      onClick={dismiss}
    >
      {/* Progress bar */}
      <div style={{
        position: "absolute", bottom: 0, left: 0,
        height: 3,
        width: `${progress}%`,
        background: sev.accent,
        boxShadow: `0 0 8px ${sev.accent}`,
        transition: "width 0.05s linear",
        borderRadius: "0 0 0 10px",
      }} />

      <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
        {/* Icon */}
        <div style={{
          width: 36, height: 36, borderRadius: 8, flexShrink: 0,
          background: `${sev.border}22`,
          border: `1px solid ${sev.border}44`,
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 18,
        }}>
          {sev.icon}
        </div>

        {/* Content */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
            <span style={{ color: sev.accent, fontWeight: 800, fontSize: 11, letterSpacing: 1.5 }}>
              {sev.label}
            </span>
            <span style={{ color: "#444", fontSize: 10 }}>
              {new Date(toast.timestamp).toLocaleTimeString()}
            </span>
          </div>
          <div style={{ color: "#ccc", fontSize: 12, marginBottom: 6, fontFamily: "monospace" }}>
            <span style={{ color: sev.accent }}>{toast.src_ip}</span>
            <span style={{ color: "#555" }}> → </span>
            <span style={{ color: "#888" }}>{toast.attack_type}</span>
          </div>
          <div style={{ color: "#666", fontSize: 11, marginBottom: 10 }}>
            Risk: <span style={{ color: sev.accent, fontWeight: "bold" }}>
              {(toast.risk_score * 100).toFixed(0)}%
            </span>
            <span style={{ marginLeft: 10 }}>Protocol: {toast.protocol?.toUpperCase()}</span>
          </div>

          {/* Action buttons */}
          <div style={{ display: "flex", gap: 8 }} onClick={e => e.stopPropagation()}>
            <button
              onClick={() => { onAction(toast); dismiss(); }}
              style={{
                background: `${sev.border}22`,
                border: `1px solid ${sev.border}`,
                color: sev.accent,
                borderRadius: 6,
                padding: "5px 12px",
                fontSize: 10,
                fontWeight: 700,
                letterSpacing: 1,
                cursor: "pointer",
                transition: "all 0.2s",
              }}
              onMouseEnter={e => e.target.style.background = `${sev.border}44`}
              onMouseLeave={e => e.target.style.background = `${sev.border}22`}
            >
              🔒 QUARANTINE
            </button>
            <button
              onClick={dismiss}
              style={{
                background: "transparent",
                border: "1px solid #2a2a45",
                color: "#555",
                borderRadius: 6,
                padding: "5px 12px",
                fontSize: 10,
                fontWeight: 600,
                cursor: "pointer",
                transition: "all 0.2s",
              }}
              onMouseEnter={e => { e.target.style.borderColor = "#444"; e.target.style.color = "#888"; }}
              onMouseLeave={e => { e.target.style.borderColor = "#2a2a45"; e.target.style.color = "#555"; }}
            >
              IGNORE
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ToastManager({ messages }) {
  const [toasts, setToasts] = useState([]);
  const [dialogAlert, setDialogAlert] = useState(null);
  const [quarantined, setQuarantined] = useState(new Set());
  const seenRef = useRef(new Set());

  useEffect(() => {
    if (!messages.length) return;
    const latest = messages[0];
    const key = `${latest.src_ip}-${latest.timestamp}`;
    if (seenRef.current.has(key)) return;
    if (!["CRITICAL", "HIGH"].includes(latest.severity)) return;
    seenRef.current.add(key);

    const toast = { ...latest, id: `${key}-${Date.now()}` };
    setToasts(prev => [toast, ...prev].slice(0, 5));
  }, [messages]);

  const dismiss = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  const handleQuarantine = useCallback((alert) => {
    setDialogAlert(alert);
  }, []);

  const confirmQuarantine = useCallback(() => {
    if (!dialogAlert) return;
    setQuarantined(prev => new Set([...prev, dialogAlert.src_ip]));
    setDialogAlert(null);
    // Show success toast
    const successToast = {
      id: `quarantine-success-${Date.now()}`,
      severity: "QUARANTINE_SUCCESS",
      src_ip: dialogAlert.src_ip,
      message: `Device ${dialogAlert.src_ip} has been quarantined`,
      timestamp: new Date().toISOString(),
    };
    setToasts(prev => [successToast, ...prev].slice(0, 5));
  }, [dialogAlert]);

  return (
    <>
      {/* Toast stack */}
      <div style={{
        position: "fixed",
        top: 20,
        right: 20,
        zIndex: 9000,
        display: "flex",
        flexDirection: "column",
        alignItems: "flex-end",
        pointerEvents: "none",
      }}>
        {toasts.map(t => (
          <div key={t.id} style={{ pointerEvents: "auto" }}>
            {t.severity === "QUARANTINE_SUCCESS" ? (
              <SuccessToast toast={t} onDismiss={dismiss} />
            ) : (
              <Toast toast={t} onDismiss={dismiss} onAction={handleQuarantine} />
            )}
          </div>
        ))}
      </div>

      {/* Quarantine Dialog */}
      {dialogAlert && (
        <QuarantineDialog
          alert={dialogAlert}
          onQuarantine={confirmQuarantine}
          onIgnore={() => setDialogAlert(null)}
        />
      )}

      {/* Quarantine badge overlay on devices */}
      {quarantined.size > 0 && (
        <div style={{
          position: "fixed", bottom: 20, left: 20,
          background: "#0d0d1e",
          border: "1px solid #ff2d2d",
          borderRadius: 8,
          padding: "8px 14px",
          zIndex: 8000,
          fontSize: 11,
          color: "#ff2d2d",
          fontFamily: "monospace",
          boxShadow: "0 0 16px #ff2d2d33",
        }}>
          🔒 {quarantined.size} device{quarantined.size > 1 ? "s" : ""} quarantined
        </div>
      )}
    </>
  );
}

function SuccessToast({ toast, onDismiss }) {
  const [visible, setVisible] = useState(false);
  const [exiting, setExiting] = useState(false);

  useEffect(() => {
    requestAnimationFrame(() => setVisible(true));
    const t = setTimeout(() => {
      setExiting(true);
      setTimeout(() => onDismiss(toast.id), 350);
    }, 4000);
    return () => clearTimeout(t);
  }, []);

  return (
    <div style={{
      background: "linear-gradient(135deg, #001a00, #002d00)",
      border: "1px solid #4caf50",
      borderRadius: 10,
      padding: "12px 16px",
      width: 320,
      boxShadow: "0 0 20px #4caf5044",
      marginBottom: 10,
      transform: visible && !exiting ? "translateX(0) scale(1)" : "translateX(100%) scale(0.95)",
      opacity: visible && !exiting ? 1 : 0,
      transition: "transform 0.35s cubic-bezier(0.34,1.56,0.64,1), opacity 0.35s ease",
      display: "flex", alignItems: "center", gap: 12,
    }}>
      <span style={{ fontSize: 22 }}>✅</span>
      <div>
        <div style={{ color: "#4caf50", fontWeight: 800, fontSize: 11, letterSpacing: 1 }}>
          DEVICE QUARANTINED
        </div>
        <div style={{ color: "#888", fontSize: 11, marginTop: 2, fontFamily: "monospace" }}>
          {toast.src_ip} — traffic blocked
        </div>
      </div>
    </div>
  );
}
