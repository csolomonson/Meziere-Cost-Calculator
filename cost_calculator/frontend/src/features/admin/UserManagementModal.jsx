import React, { useEffect, useState } from "react";

import { readApiResponse } from "../../api/client.js";
import { Button } from "../../components/ui.jsx";

export function UserManagementModal({ onClose }) {
  const [users, setUsers] = useState([]), [loading, setLoading] = useState(true), [message, setMessage] = useState(""), [newUser, setNewUser] = useState({ username: "", password: "", groups: "users" });
  async function loadUsers() {
    try {
      setLoading(true);
      const payload = await readApiResponse(await fetch("/api/admin/users"));
      setUsers((payload.users || []).map((user) => ({ ...user, groupText: (user.groups || []).join(", "), newPassword: "" })));
      setMessage("");
    } catch (error) {
      setMessage(error.message || "Could not load users.");
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => { loadUsers(); }, []);
  function groupsFromText(value) { return value.split(",").map((group) => group.trim()).filter(Boolean); }
  function updateRow(username, field, value) { setUsers((rows) => rows.map((row) => row.username === username ? { ...row, [field]: value } : row)); }
  async function add(event) {
    event.preventDefault();
    try {
      const payload = await readApiResponse(await fetch("/api/admin/users", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username: newUser.username.trim(), password: newUser.password, groups: groupsFromText(newUser.groups) }) }));
      setUsers((payload.users || []).map((user) => ({ ...user, groupText: (user.groups || []).join(", "), newPassword: "" })));
      setNewUser({ username: "", password: "", groups: "users" });
      setMessage("User added.");
    } catch (error) { setMessage(error.message || "Could not add user."); }
  }
  async function save(row) {
    try {
      const body = { groups: groupsFromText(row.groupText) };
      if (row.newPassword) body.password = row.newPassword;
      const payload = await readApiResponse(await fetch("/api/admin/users/" + encodeURIComponent(row.username), { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }));
      setUsers((payload.users || []).map((user) => ({ ...user, groupText: (user.groups || []).join(", "), newPassword: "" })));
      setMessage("Changes saved for " + row.username + ".");
    } catch (error) { setMessage(error.message || "Could not save user."); }
  }
  async function remove(row) {
    if (!window.confirm("Delete user " + row.username + "?")) return;
    try {
      const payload = await readApiResponse(await fetch("/api/admin/users/" + encodeURIComponent(row.username), { method: "DELETE" }));
      setUsers((payload.users || []).map((user) => ({ ...user, groupText: (user.groups || []).join(", "), newPassword: "" })));
      setMessage("User deleted.");
    } catch (error) { setMessage(error.message || "Could not delete user."); }
  }
  return <div className="modal-backdrop"><section className="user-management-modal"><header><div><span className="eyebrow">Administration</span><h2>User management</h2></div><Button tone="secondary" onClick={onClose}>Close</Button></header><div className="user-management-body">
    <form className="add-user-form" onSubmit={add}><h3>Add user</h3><label className="field"><span>Username</span><input autoComplete="off" value={newUser.username} onChange={(event) => setNewUser({ ...newUser, username: event.target.value })} required /></label><label className="field"><span>Password</span><input type="password" autoComplete="new-password" minLength="8" value={newUser.password} onChange={(event) => setNewUser({ ...newUser, password: event.target.value })} required /></label><label className="field"><span>Groups</span><input value={newUser.groups} onChange={(event) => setNewUser({ ...newUser, groups: event.target.value })} placeholder="users, administrators" /></label><Button type="submit">Add user</Button></form>
    <div className="managed-users"><div className="managed-user-head"><strong>User</strong><strong>Groups</strong><strong>New password</strong><span></span></div>{loading ? <div className="empty-state">Loading users…</div> : users.map((row) => <div className="managed-user-row" key={row.username}><strong>{row.username}</strong><input aria-label={row.username + " groups"} value={row.groupText} onChange={(event) => updateRow(row.username, "groupText", event.target.value)} /><input aria-label={row.username + " new password"} type="password" autoComplete="new-password" minLength="8" value={row.newPassword} onChange={(event) => updateRow(row.username, "newPassword", event.target.value)} placeholder="Leave unchanged" /><div><Button onClick={() => save(row)}>Save</Button><Button tone="secondary" onClick={() => remove(row)}>Delete</Button></div></div>)}</div>
    {message && <div className={message.toLowerCase().includes("could not") || message.toLowerCase().includes("cannot") ? "error-box" : "middle-note"}>{message}</div>}
  </div></section></div>;
}


