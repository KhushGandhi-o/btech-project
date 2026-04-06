(() => {
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("file-input");
  const processBtn = document.getElementById("process-btn");
  const resetBtn = document.getElementById("reset-btn");
  const fileMeta = document.getElementById("file-meta");
  const statusEl = document.getElementById("status");
  const transcriptOut = document.getElementById("transcript-out");
  const soapCardsWrap = document.getElementById("soap-cards-wrap");
  const soapCards = document.getElementById("soap-cards");
  const soapRaw = document.getElementById("soap-out");
  const soapTabs = document.querySelectorAll(".soap-tab");
  const toast = document.getElementById("toast");
  const tabs = document.querySelectorAll(".tab");

  let selectedFile = null;
  let rawTranscript = "";
  let cleanedTranscript = "";
  let soapNoteText = "";

  function setSoapTab(which) {
    const showCards = which === "cards";
    soapCardsWrap.classList.toggle("hidden", !showCards);
    soapRaw.classList.toggle("hidden", showCards);
    soapTabs.forEach((t) => {
      const active = t.dataset.soapTab === which;
      t.classList.toggle("active", active);
      t.setAttribute("aria-selected", active ? "true" : "false");
    });
  }

  function showToast(message, isError = false) {
    toast.textContent = message;
    toast.classList.remove("hidden", "error");
    if (isError) toast.classList.add("error");
    clearTimeout(showToast._t);
    showToast._t = setTimeout(() => toast.classList.add("hidden"), 3200);
  }

  function formatBytes(n) {
    if (n < 1024) return `${n} B`;
    if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
    return `${(n / (1024 * 1024)).toFixed(1)} MB`;
  }

  function setFile(file) {
    selectedFile = file;
    if (!file) {
      fileMeta.classList.add("hidden");
      processBtn.disabled = true;
      resetBtn.classList.add("hidden");
      return;
    }
    fileMeta.classList.remove("hidden");
    fileMeta.innerHTML = `<strong>${file.name}</strong> · ${formatBytes(file.size)} · ${file.type || "audio"}`;
    processBtn.disabled = false;
    resetBtn.classList.remove("hidden");
  }

  function setStatus(text, isError = false) {
    if (!text) {
      statusEl.classList.add("hidden");
      return;
    }
    statusEl.classList.remove("hidden", "error");
    statusEl.textContent = text;
    if (isError) statusEl.classList.add("error");
  }

  function renderSoap(soap) {
    soapCards.classList.remove("empty-state");
    soapCards.innerHTML = "";
    const order = ["Subjective", "Objective", "Assessment", "Plan"];
    for (const key of order) {
      const items = soap[key] || [];
      const card = document.createElement("div");
      card.className = "soap-card";
      const h = document.createElement("h3");
      h.textContent = key;
      card.appendChild(h);
      if (items.length === 0) {
        const p = document.createElement("p");
        p.style.margin = "0";
        p.style.color = "var(--muted)";
        p.style.fontSize = "0.85rem";
        p.textContent = "(none extracted)";
        card.appendChild(p);
      } else {
        const ul = document.createElement("ul");
        for (const line of items) {
          const li = document.createElement("li");
          li.textContent = line;
          ul.appendChild(li);
        }
        card.appendChild(ul);
      }
      soapCards.appendChild(card);
    }
  }

  function setTranscriptTab(which) {
    const isRaw = which === "raw";
    transcriptOut.textContent = isRaw ? rawTranscript : cleanedTranscript;
    transcriptOut.classList.toggle("empty", !(isRaw ? rawTranscript : cleanedTranscript));
    tabs.forEach((t) => {
      const active = t.dataset.tab === which;
      t.classList.toggle("active", active);
      t.setAttribute("aria-selected", active ? "true" : "false");
    });
  }

  tabs.forEach((t) => {
    t.addEventListener("click", () => setTranscriptTab(t.dataset.tab));
  });

  soapTabs.forEach((t) => {
    t.addEventListener("click", () => setSoapTab(t.dataset.soapTab));
  });

  dropzone.addEventListener("click", (e) => {
    if (e.target.closest(".browse-btn")) {
      fileInput.click();
      return;
    }
    if (!e.target.closest("button")) fileInput.click();
  });

  dropzone.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      fileInput.click();
    }
  });

  fileInput.addEventListener("change", () => {
    const f = fileInput.files?.[0];
    setFile(f || null);
  });

  ["dragenter", "dragover"].forEach((ev) => {
    dropzone.addEventListener(ev, (e) => {
      e.preventDefault();
      dropzone.classList.add("dragover");
    });
  });

  ["dragleave", "drop"].forEach((ev) => {
    dropzone.addEventListener(ev, (e) => {
      e.preventDefault();
      dropzone.classList.remove("dragover");
    });
  });

  dropzone.addEventListener("drop", (e) => {
    const f = e.dataTransfer?.files?.[0];
    if (f) {
      fileInput.value = "";
      setFile(f);
    }
  });

  resetBtn.addEventListener("click", () => {
    selectedFile = null;
    fileInput.value = "";
    setFile(null);
    setStatus("");
    rawTranscript = "";
    cleanedTranscript = "";
    transcriptOut.textContent = "Upload audio and run the pipeline to see the transcript.";
    transcriptOut.classList.add("empty");
    soapCards.innerHTML =
      '<p class="placeholder">Structured Subjective, Objective, Assessment, and Plan will appear here.</p>';
    soapCards.classList.add("empty-state");
    soapNoteText = "";
    soapRaw.textContent = "";
    setSoapTab("cards");
    setTranscriptTab("raw");
  });

  processBtn.addEventListener("click", async () => {
    if (!selectedFile) return;
    setStatus("Transcribing and extracting entities — first run may take several minutes…");
    processBtn.disabled = true;

    const fd = new FormData();
    fd.append("file", selectedFile);

    try {
      const res = await fetch("/api/process-audio", {
        method: "POST",
        body: fd,
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = data.detail || res.statusText || "Request failed";
        const msg = typeof detail === "string" ? detail : JSON.stringify(detail);
        throw new Error(msg);
      }

      rawTranscript = data.transcript || "";
      cleanedTranscript = data.cleaned_dialogue || "";
      transcriptOut.classList.remove("empty");
      setTranscriptTab(document.querySelector(".tab.active")?.dataset.tab || "raw");

      renderSoap(data.soap || {});
      soapNoteText = data.soap_note || "";
      soapRaw.textContent = soapNoteText;
      setSoapTab("cards");

      setStatus("Done.");
      showToast("Pipeline finished");
    } catch (err) {
      setStatus(err.message || "Something went wrong", true);
      showToast(err.message || "Error", true);
    } finally {
      processBtn.disabled = !selectedFile;
    }
  });

  document.querySelectorAll(".copy-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = btn.getAttribute("data-copy-target");
      const el = document.getElementById(id);
      let text = el?.textContent || "";
      if (id === "transcript-out") {
        const active = document.querySelector(".tab.active")?.dataset.tab;
        text = active === "cleaned" ? cleanedTranscript : rawTranscript;
      }
      if (id === "soap-out") {
        text = soapNoteText || soapRaw.textContent;
      }
      try {
        await navigator.clipboard.writeText(text);
        showToast("Copied");
      } catch {
        showToast("Copy failed", true);
      }
    });
  });
})();
