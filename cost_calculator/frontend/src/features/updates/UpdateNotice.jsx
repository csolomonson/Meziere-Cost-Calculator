import React, { useEffect, useState } from "react";

import { readApiResponse } from "../../api/client.js";
import { Button } from "../../components/ui.jsx";

export function UpdateNotice() {
  const [update, setUpdate] = useState(null), [message, setMessage] = useState("");
  useEffect(() => {
    let active = true;
    fetch("/api/update").then(readApiResponse).then((payload) => { if (active) setUpdate(payload); }).catch(() => {});
    return () => { active = false; };
  }, []);
  if (!update?.update_available) return null;
  async function install() {
    try {
      setMessage("Requesting update…");
      await readApiResponse(await fetch("/api/update/install", { method: "POST" }));
      setMessage("Update requested. This page will remain available during staging.");
    } catch (error) {
      setMessage(error.message || "Could not request the update.");
    }
  }
  return <aside className="update-notice"><span>Version {update.available_version} is available.</span>{update.can_install && <Button onClick={install}>Install update</Button>}{message && <small>{message}</small>}</aside>;
}


