document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("upload-form");
  const fileInput = document.getElementById("file-input");
  const uploadBtn = document.getElementById("upload-btn");
  const statusEl = document.getElementById("status");
  const progressContainer = document.getElementById("progress-container");
  const progressBar = document.getElementById("progress-bar");
  const progressLabel = document.getElementById("progress-label");
  const statusText = document.getElementById("status-text");

  let currentJobId = null;
  let pollTimer = null;

  function setStatus(message, type) {
    statusEl.textContent = message || "";
    statusEl.className = type || "";
  }

  function startPolling(jobId) {
    if (pollTimer) {
      clearInterval(pollTimer);
    }
    pollTimer = setInterval(async () => {
      try {
        const res = await fetch(`/api/uploads/${jobId}`);
        if (!res.ok) {
          throw new Error(`Status check failed with ${res.status}`);
        }
        const data = await res.json();
        const total = data.total_rows || 0;
        const processed = data.processed_rows || 0;
        const status = data.status || "unknown";

        statusText.textContent = status;

        if (total > 0) {
          const pct = Math.round((processed / total) * 100);
          progressBar.value = pct;
          progressLabel.textContent = `${pct}% (${processed}/${total})`;
        } else {
          progressBar.value = 0;
          progressLabel.textContent = `${processed} rows processed`;
        }

        if (status === "completed") {
          clearInterval(pollTimer);
          setStatus("Import completed successfully.", "success");
          uploadBtn.disabled = false;
          fileInput.disabled = false;
        } else if (status === "failed") {
          clearInterval(pollTimer);
          setStatus(data.error_message || "Import failed.", "error");
          uploadBtn.disabled = false;
          fileInput.disabled = false;
        }
      } catch (err) {
        console.error(err);
        setStatus("Error checking upload status.", "error");
      }
    }, 2000);
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    setStatus("", "");
    if (!fileInput.files.length) {
      setStatus("Please select a CSV file.", "error");
      return;
    }

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    uploadBtn.disabled = true;
    fileInput.disabled = true;
    progressContainer.style.display = "block";
    progressBar.value = 0;
    progressLabel.textContent = "0%";
    statusText.textContent = "Queued…";

    try {
      const res = await fetch("/api/uploads", {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        throw new Error(`Upload failed with status ${res.status}`);
      }
      const data = await res.json();
      currentJobId = data.id || data.job_id;
      if (!currentJobId) {
        throw new Error("Upload response missing job id");
      }

      setStatus("File uploaded, processing started.", "success");
      statusText.textContent = "running";
      startPolling(currentJobId);
    } catch (err) {
      console.error(err);
      setStatus("Upload failed: " + err.message, "error");
      uploadBtn.disabled = false;
      fileInput.disabled = false;
      progressContainer.style.display = "none";
    }
  });
});
