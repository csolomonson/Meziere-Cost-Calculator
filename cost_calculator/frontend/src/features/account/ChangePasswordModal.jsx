import React, { useState } from "react";

import { readApiResponse } from "../../api/client.js";
import { Button } from "../../components/ui.jsx";


export function ChangePasswordModal({ onClose }) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function submit(event) {
    event.preventDefault();
    if (newPassword !== confirmation) {
      setError("The new passwords do not match.");
      return;
    }
    try {
      setSaving(true);
      setError("");
      await readApiResponse(await fetch("/api/account/password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
      }));
      window.location.assign("/logout");
    } catch (exception) {
      setError(exception.message || "The password could not be changed.");
      setSaving(false);
    }
  }

  return <div className="modal-backdrop"><section className="account-modal"><header><div><span className="eyebrow">Account</span><h2>Change password</h2></div><Button tone="secondary" onClick={onClose}>Close</Button></header><form onSubmit={submit}><label className="field"><span>Current password</span><input type="password" autoComplete="current-password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} required /></label><label className="field"><span>New password</span><input type="password" autoComplete="new-password" minLength="8" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} required /></label><label className="field"><span>Confirm new password</span><input type="password" autoComplete="new-password" minLength="8" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} required /></label>{error && <div className="error-box">{error}</div>}<div className="history-actions"><Button type="submit" disabled={saving}>{saving ? "Changing…" : "Change password"}</Button><Button type="button" tone="secondary" onClick={onClose}>Cancel</Button></div></form></section></div>;
}
