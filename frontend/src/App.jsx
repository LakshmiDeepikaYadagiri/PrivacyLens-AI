
import { useRef, useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";
const MAX_CHARACTERS = 25000;
const MAX_FILE_BYTES = 10 * 1024 * 1024;

function App() {
  const [text, setText] = useState("");
  const [results, setResults] = useState(null);
  const [redactedText, setRedactedText] = useState(null);
  const [riskScore, setRiskScore] = useState(null);
  const [loading, setLoading] = useState("");
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const [uploadedFile, setUploadedFile] = useState(null);

  const fileInputRef = useRef(null);

  const clearResults = () => {
    setResults(null);
    setRedactedText(null);
    setRiskScore(null);
    setError("");
    setCopied(false);
  };

  const getErrorMessage = async (response) => {
    const data = await response.json().catch(() => null);

    if (typeof data?.detail === "string") {
      return data.detail;
    }

    return `Server error: ${response.status}`;
  };

  const sendRequest = async (endpoint, inputText) => {
    const response = await fetch(`${API_URL}${endpoint}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ text: inputText }),
    });

    if (!response.ok) {
      throw new Error(await getErrorMessage(response));
    }

    return response.json();
  };

  const analyze = async (type) => {
    if (!text.trim() || loading) return;

    clearResults();

    if (text.length > MAX_CHARACTERS) {
      setError("Maximum input is 25,000 characters.");
      return;
    }

    const endpoints = {
      detect: "/detect",
      redact: "/redact",
      risk: "/risk-score",
    };

    setLoading(type);

    try {
      const data = await sendRequest(
        endpoints[type],
        text
      );

      if (type === "detect") {
        setResults(data);
      } else if (type === "redact") {
        setRedactedText(data);
      } else {
        setRiskScore(data);
      }
    } catch (err) {
      setError(`Analysis failed: ${err.message}`);
    } finally {
      setLoading("");
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files?.[0];

    if (!file || loading) return;

    clearResults();
    setUploadedFile(null);
    setText("");

    event.target.value = "";

    const extension = file.name
      .split(".")
      .pop()
      ?.toLowerCase();

    if (!["txt", "pdf", "docx"].includes(extension)) {
      setError("Please select a TXT, PDF, or DOCX file.");
      return;
    }

    if (file.size > MAX_FILE_BYTES) {
      setError("Maximum file size is 10 MB.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    setLoading("upload");

    try {
      const response = await fetch(`${API_URL}/upload`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(await getErrorMessage(response));
      }

      const data = await response.json();

      if (data.text.length > MAX_CHARACTERS) {
        throw new Error(
          "Extracted text exceeds 25,000 characters."
        );
      }

      setText(data.text);

      setUploadedFile({
        name: data.filename,
        type: data.file_type,
        size: data.file_size,
        characters: data.character_count,
      });
    } catch (err) {
      setError(`Upload failed: ${err.message}`);
    } finally {
      setLoading("");
    }
  };

  const clearAll = () => {
    setText("");
    setUploadedFile(null);
    clearResults();

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleTextChange = (event) => {
    setText(event.target.value);
    setUploadedFile(null);
    clearResults();
  };

  const copyRedactedText = async () => {
    try {
      await navigator.clipboard.writeText(
        redactedText?.redacted_text || ""
      );
      setCopied(true);
    } catch {
      setError("Could not copy text.");
    }
  };

  // Download TXT, PDF, or DOCX from backend.
  const downloadRedactedDocument = async (format) => {
    if (!redactedText || !text.trim() || loading) return;

    setError("");
    setLoading("download");

    try {
      const response = await fetch(`${API_URL}/export`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          text,
          file_format: format,
        }),
      });

      if (!response.ok) {
        throw new Error(await getErrorMessage(response));
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);

      const link = document.createElement("a");
      link.href = url;
      link.download = `PrivacyLens_Redacted.${format}`;

      document.body.appendChild(link);
      link.click();
      link.remove();

      setTimeout(() => {
        URL.revokeObjectURL(url);
      }, 1000);
    } catch (err) {
      setError(`Download failed: ${err.message}`);
    } finally {
      setLoading("");
    }
  };

  const riskValue = Math.min(
    100,
    Math.max(0, Number(riskScore?.risk_score) || 0)
  );

  const riskLevel = riskScore?.risk_level || "Unknown";

  const riskColor =
    riskLevel === "High"
      ? "#f87171"
      : riskLevel === "Medium"
      ? "#fbbf24"
      : "#34d399";

  const renderChunkInfo = (data) => {
    if (data?.total_chunks == null) return null;

    return (
      <p className="chunk-info">
        ✓ Processed in {data.total_chunks} chunk(s)
      </p>
    );
  };

  return (
    <div className="app-shell">
      <div className="ambient ambient-one" />
      <div className="ambient ambient-two" />

      <div className="dashboard">
        <header className="topbar">
          <div className="brand">
            <div className="brand-icon">✦</div>

            <div>
              <h1>
                PrivacyLens <span>AI</span>
              </h1>
              <p>INTELLIGENT PRIVACY PROTECTION</p>
            </div>
          </div>

          <div className="status-pill">
            <span className="status-dot" />
            Privacy Analysis
          </div>
        </header>

        <section className="hero">
          <div className="eyebrow">
            AI-POWERED TEXT SECURITY
          </div>

          <h2>
            Your data deserves
            <br />
            <span>better protection.</span>
          </h2>

          <p>
            Detect sensitive information, redact personal
            details, and understand privacy risks in one
            intelligent workspace.
          </p>
        </section>

        <main className="workspace">
          {/* INPUT PANEL */}
          <section className="panel input-panel">
            <div className="panel-heading">
              <div>
                <div className="section-label">
                  01 / INPUT
                </div>

                <h3>Analyze your text</h3>

                <p>
                  Paste text or upload a document to begin.
                </p>
              </div>

              <div className="panel-symbol">⌘</div>
            </div>

            {/* DOCUMENT UPLOAD */}
            <div className="upload-section">
              <input
                ref={fileInputRef}
                type="file"
                accept=".txt,.pdf,.docx"
                onChange={handleFileUpload}
                disabled={Boolean(loading)}
                style={{ display: "none" }}
              />

              <button
                type="button"
                className="upload-button"
                onClick={() => fileInputRef.current?.click()}
                disabled={Boolean(loading)}
              >
                <span className="upload-icon">↑</span>

                <span className="upload-label">
                  <strong>Upload a document</strong>
                  <small>
                    TXT, PDF or DOCX · Maximum 10 MB
                  </small>
                </span>
              </button>

              {uploadedFile && (
                <div className="uploaded-file">
                  <div className="uploaded-file-details">
                    <span className="uploaded-file-icon">
                      📄
                    </span>

                    <div className="uploaded-file-text">
                      <strong title={uploadedFile.name}>
                        {uploadedFile.name}
                      </strong>

                      <small>
                        {uploadedFile.type} ·{" "}
                        {(uploadedFile.size / 1024).toFixed(1)}
                        {" "}KB ·{" "}
                        {uploadedFile.characters.toLocaleString()}
                        {" "}characters
                      </small>
                    </div>
                  </div>

                  <button
                    type="button"
                    className="remove-file"
                    onClick={clearAll}
                    disabled={Boolean(loading)}
                    aria-label="Remove uploaded file"
                  >
                    ×
                  </button>
                </div>
              )}
            </div>

            <div className="upload-divider">
              <span>OR PASTE TEXT</span>
            </div>

            <textarea
              className="text-input"
              placeholder={
                "Enter text containing sensitive information...\n\nExample: My name is John Smith and my email is john@example.com."
              }
              value={text}
              onChange={handleTextChange}
              disabled={Boolean(loading)}
              maxLength={MAX_CHARACTERS}
              spellCheck={false}
            />

            <div className="input-meta">
              <span>
                {text.length.toLocaleString()} /{" "}
                {MAX_CHARACTERS.toLocaleString()} characters
              </span>

              <span>
                {Math.round(
                  (text.length / MAX_CHARACTERS) * 100
                )}% used
              </span>
            </div>

            <div className="character-track">
              <div
                className="character-fill"
                style={{
                  width: `${
                    (text.length / MAX_CHARACTERS) * 100
                  }%`,
                }}
              />
            </div>

            <div className="action-grid">
              <button
                className="action-btn primary"
                onClick={() => analyze("detect")}
                disabled={Boolean(loading) || !text.trim()}
              >
                <span className="button-icon">◎</span>
                {loading === "detect"
                  ? "Detecting..."
                  : "Detect Sensitive Data"}
              </button>

              <button
                className="action-btn secondary"
                onClick={() => analyze("redact")}
                disabled={Boolean(loading) || !text.trim()}
              >
                <span className="button-icon">◈</span>
                {loading === "redact"
                  ? "Redacting..."
                  : "Redact Text"}
              </button>

              <button
                className="action-btn secondary"
                onClick={() => analyze("risk")}
                disabled={Boolean(loading) || !text.trim()}
              >
                <span className="button-icon">◉</span>
                {loading === "risk"
                  ? "Calculating..."
                  : "Calculate Risk Score"}
              </button>

              <button
                className="action-btn clear"
                onClick={clearAll}
                disabled={Boolean(loading)}
              >
                ↺ Clear All
              </button>
            </div>
          </section>

          {/* RESULTS PANEL */}
          <section className="panel results-panel">
            <div className="panel-heading">
              <div>
                <div className="section-label">
                  02 / INSIGHTS
                </div>

                <h3>Analysis results</h3>
                <p>Your privacy insights appear here.</p>
              </div>

              <div className="panel-symbol">✧</div>
            </div>

            {loading && loading !== "download" && (
              <div className="empty-state">
                <div className="loading-spinner" />

                <h4>
                  {loading === "upload"
                    ? "Extracting document text"
                    : "Analyzing your text"}
                </h4>

                <p>Please wait while we process your request.</p>
              </div>
            )}

            {error && (
              <div className="error-box">
                {error}
              </div>
            )}

            {!results &&
              !redactedText &&
              !riskScore &&
              !error &&
              !loading && (
                <div className="empty-state">
                  <div className="empty-icon">✧</div>

                  <h4>Ready when you are</h4>

                  <p>
                    Upload a document or enter text,
                    then choose an analysis option.
                  </p>
                </div>
              )}

            {/* DETECTION RESULTS */}
            {results && !loading && (
              <div className="result-content">
                <div className="result-header">
                  <h4>Sensitive Data Detection</h4>

                  <span className="count-pill">
                    {results.total_detected} found
                  </span>
                </div>

                {renderChunkInfo(results)}

                {results.detections?.length > 0 ? (
                  <div className="detection-list">
                    {results.detections.map((item, index) => (
                      <div
                        className="detection-card"
                        key={index}
                      >
                        <div className="detection-top">
                          <span className="entity-tag">
                            {item.type.replaceAll("_", " ")}
                          </span>

                          <span className="confidence">
                            {(item.confidence * 100).toFixed(0)}%
                            {" "}confidence
                          </span>
                        </div>

                        <div className="detected-value">
                          {item.text}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="empty-state compact">
                    <h4>No sensitive data detected</h4>
                    <p>No recognized entities were found.</p>
                  </div>
                )}
              </div>
            )}

            {/* REDACTION AND DOWNLOAD */}
            {redactedText &&
              (!loading || loading === "download") && (
                <div className="result-content">
                  <div className="result-header">
                    <h4>Protected Text</h4>
                    <span className="safe-pill">Redacted</span>
                  </div>

                  {renderChunkInfo(redactedText)}

                  <div className="redacted-output">
                    {redactedText.redacted_text || ""}
                  </div>

                  <button
                    className="copy-btn"
                    onClick={copyRedactedText}
                    disabled={Boolean(loading)}
                  >
                    {copied
                      ? "✓ Copied!"
                      : "▢ Copy Redacted Text"}
                  </button>

                  <div className="download-section">
                    <h4>Download Protected Document</h4>

                    <p>
                      Save your redacted text in your
                      preferred file format.
                    </p>

                    <div className="download-buttons">
                      {["txt", "pdf", "docx"].map((format) => (
                        <button
                          key={format}
                          type="button"
                          className="download-btn"
                          onClick={() =>
                            downloadRedactedDocument(format)
                          }
                          disabled={Boolean(loading)}
                        >
                          <span>↓</span>
                          {loading === "download"
                            ? "Preparing..."
                            : `Download ${format.toUpperCase()}`}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}

            {/* RISK RESULTS */}
            {riskScore && !loading && (
              <div className="result-content">
                <div className="result-header">
                  <h4>Privacy Risk Assessment</h4>

                  <span
                    className="risk-pill"
                    style={{
                      color: riskColor,
                      borderColor: riskColor,
                    }}
                  >
                    {riskLevel} Risk
                  </span>
                </div>

                {renderChunkInfo(riskScore)}

                <div className="risk-summary">
                  <div className="risk-number">
                    {riskScore.risk_score}
                    <span>/100</span>
                  </div>

                  <p>Overall Privacy Risk Score</p>
                </div>

                <div className="risk-track">
                  <div
                    className="risk-fill"
                    style={{
                      width: `${riskValue}%`,
                      backgroundColor: riskColor,
                    }}
                  />
                </div>

                <div className="risk-scale">
                  <span>Low</span>
                  <span>Medium</span>
                  <span>High</span>
                </div>

                <div className="risk-detail">
                  <span>Sensitive entities detected</span>
                  <strong>{riskScore.total_detected}</strong>
                </div>
              </div>
            )}
          </section>
        </main>

        <footer className="footer">
          <span>© PrivacyLens AI</span>
          <span>Built with React · FastAPI · Python</span>
        </footer>
      </div>
    </div>
  );
}

export default App;
