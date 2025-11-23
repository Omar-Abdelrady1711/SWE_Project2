import { useState } from "react";
import api from "../services/apiClient";
import "./TestDebug.css";

export default function TestDebug() {
  const [activeTab, setActiveTab] = useState("listArtifacts");
  const [output, setOutput] = useState("");
  const [loading, setLoading] = useState(false);

  // Form states for different operations
  const [listQueries, setListQueries] = useState([{ name: "*", types: [] }]);
  const [artifactType, setArtifactType] = useState("model");
  const [artifactUrl, setArtifactUrl] = useState("");
  const [regexPattern, setRegexPattern] = useState("");
  const [getArtifactType, setGetArtifactType] = useState("model");
  const [getArtifactId, setGetArtifactId] = useState("");
  const [getArtifactByName, setGetArtifactByName] = useState("");

  const logOutput = (message, data = null) => {
    const timestamp = new Date().toLocaleTimeString();
    let logText = `[${timestamp}] ${message}`;
    if (data) {
      logText += "\n" + JSON.stringify(data, null, 2);
    }
    setOutput((prev) => prev + logText + "\n\n");
  };

  const clearOutput = () => setOutput("");

  // List Artifacts
  const handleListArtifacts = async () => {
    setLoading(true);
    try {
      const payload = listQueries.map((q) => ({
        name: q.name || "*",
        types: q.types && q.types.length > 0 ? q.types : undefined,
      }));
      logOutput("POST /artifacts", { queries: payload });
      const response = await api.post("/artifacts", payload);
      logOutput("Response:", response.data);
    } catch (error) {
      logOutput("Error:", {
        status: error.response?.status,
        data: error.response?.data,
        message: error.message,
      });
    } finally {
      setLoading(false);
    }
  };

  // Add Query Field
  const addQueryField = () => {
    setListQueries([...listQueries, { name: "", types: [] }]);
  };

  // Update Query Field
  const updateQueryField = (index, field, value) => {
    const updated = [...listQueries];
    updated[index][field] = value;
    setListQueries(updated);
  };

  // Remove Query Field
  const removeQueryField = (index) => {
    setListQueries(listQueries.filter((_, i) => i !== index));
  };

  // Ingest Artifact
  const handleIngestArtifact = async () => {
    setLoading(true);
    try {
      // Note: endpoint is at root level, not /api
      const endpoint = `/artifact/${artifactType}`;
      logOutput(`POST ${endpoint}`, { url: artifactUrl });
      
      // Try without /api prefix since endpoint is on app, not api router
      const response = await api.post(endpoint, {
        url: artifactUrl,
      });
      logOutput("Response:", response.data);
      setArtifactUrl("");
    } catch (error) {
      logOutput("Error:", {
        status: error.response?.status,
        data: error.response?.data,
        message: error.message,
      });
    } finally {
      setLoading(false);
    }
  };

  // Search by Regex
  const handleSearchByRegex = async () => {
    setLoading(true);
    try {
      logOutput("POST /artifact/byRegEx", { regex: regexPattern });
      const response = await api.post("/artifact/byRegEx", {
        regex: regexPattern,
      });
      logOutput("Response:", response.data);
    } catch (error) {
      logOutput("Error:", {
        status: error.response?.status,
        data: error.response?.data,
        message: error.message,
      });
    } finally {
      setLoading(false);
    }
  };

  // Get Artifact by Type and ID
  const handleGetArtifact = async () => {
    setLoading(true);
    try {
      logOutput(
        `GET /artifact/${getArtifactType}/${getArtifactId}`
      );
      const response = await api.get(
        `/artifact/${getArtifactType}/${getArtifactId}`
      );
      logOutput("Response:", response.data);
    } catch (error) {
      logOutput("Error:", {
        status: error.response?.status,
        data: error.response?.data,
        message: error.message,
      });
    } finally {
      setLoading(false);
    }
  };

  // Get Artifact by Name
  const handleGetArtifactByName = async () => {
    setLoading(true);
    try {
      logOutput(`GET /artifact/byName/${getArtifactByName}`);
      const response = await api.get(
        `/artifact/byName/${getArtifactByName}`
      );
      logOutput("Response:", response.data);
    } catch (error) {
      logOutput("Error:", {
        status: error.response?.status,
        data: error.response?.data,
        message: error.message,
      });
    } finally {
      setLoading(false);
    }
  };

  // Health Check
  const handleHealthCheck = async () => {
    setLoading(true);
    try {
      logOutput("GET /health");
      const response = await api.get("/health");
      logOutput("Response:", response.data);
    } catch (error) {
      logOutput("Error:", {
        status: error.response?.status,
        data: error.response?.data,
        message: error.message,
      });
    } finally {
      setLoading(false);
    }
  };

  // Reset System
  const handleReset = async () => {
    if (window.confirm("Are you sure you want to reset the system?")) {
      setLoading(true);
      try {
        logOutput("DELETE /reset");
        const response = await api.delete("/reset");
        logOutput("Response:", response.data);
      } catch (error) {
        logOutput("Error:", {
          status: error.response?.status,
          data: error.response?.data,
          message: error.message,
        });
      } finally {
        setLoading(false);
      }
    }
  };

  // Get All Artifacts
  const handleGetAllArtifacts = async () => {
    setLoading(true);
    try {
      logOutput("GET /artifact");
      const response = await api.get("/artifact");
      logOutput("Response:", response.data);
    } catch (error) {
      logOutput("Error:", {
        status: error.response?.status,
        data: error.response?.data,
        message: error.message,
      });
    } finally {
      setLoading(false);
    }
  };

  // Get Tracks
  const handleGetTracks = async () => {
    setLoading(true);
    try {
      logOutput("GET /tracks");
      const response = await api.get("/tracks");
      logOutput("Response:", response.data);
    } catch (error) {
      logOutput("Error:", {
        status: error.response?.status,
        data: error.response?.data,
        message: error.message,
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="test-debug-container">
      <div className="test-header">
        <h1>Backend Testing & Debug Console</h1>
        <button className="clear-btn" onClick={clearOutput}>
          Clear Output
        </button>
      </div>

      <div className="test-content">
        <div className="tabs">
          <button
            className={activeTab === "listArtifacts" ? "tab active" : "tab"}
            onClick={() => setActiveTab("listArtifacts")}
          >
            List Artifacts
          </button>
          <button
            className={activeTab === "ingest" ? "tab active" : "tab"}
            onClick={() => setActiveTab("ingest")}
          >
            Ingest Artifact
          </button>
          <button
            className={activeTab === "search" ? "tab active" : "tab"}
            onClick={() => setActiveTab("search")}
          >
            Search by Regex
          </button>
          <button
            className={activeTab === "getArtifact" ? "tab active" : "tab"}
            onClick={() => setActiveTab("getArtifact")}
          >
            Get Artifact
          </button>
          <button
            className={activeTab === "getByName" ? "tab active" : "tab"}
            onClick={() => setActiveTab("getByName")}
          >
            Get by Name
          </button>
          <button
            className={activeTab === "getAllArtifacts" ? "tab active" : "tab"}
            onClick={() => setActiveTab("getAllArtifacts")}
          >
            Get All Artifacts
          </button>
          <button
            className={activeTab === "utility" ? "tab active" : "tab"}
            onClick={() => setActiveTab("utility")}
          >
            Utility
          </button>
        </div>

        <div className="tab-content">
          {/* List Artifacts Tab */}
          {activeTab === "listArtifacts" && (
            <div className="form-section">
              <h2>List Artifacts - POST /artifacts</h2>
              <div className="queries-container">
                {listQueries.map((query, index) => (
                  <div key={index} className="query-field">
                    <div className="query-inputs">
                      <div className="input-group">
                        <label>Name:</label>
                        <input
                          type="text"
                          placeholder="e.g., * for all or artifact name"
                          value={query.name}
                          onChange={(e) =>
                            updateQueryField(index, "name", e.target.value)
                          }
                        />
                      </div>
                      <div className="input-group">
                        <label>Types (comma-separated):</label>
                        <input
                          type="text"
                          placeholder="e.g., model,dataset,code"
                          value={query.types.join(",")}
                          onChange={(e) =>
                            updateQueryField(
                              index,
                              "types",
                              e.target.value.split(",").filter((t) => t.trim())
                            )
                          }
                        />
                      </div>
                    </div>
                    {listQueries.length > 1 && (
                      <button
                        className="remove-btn"
                        onClick={() => removeQueryField(index)}
                      >
                        Remove
                      </button>
                    )}
                  </div>
                ))}
              </div>
              <button
                className="add-query-btn"
                onClick={addQueryField}
              >
                Add Query
              </button>
              <button
                className="submit-btn"
                onClick={handleListArtifacts}
                disabled={loading}
              >
                {loading ? "Loading..." : "List Artifacts"}
              </button>
            </div>
          )}

          {/* Ingest Artifact Tab */}
          {activeTab === "ingest" && (
            <div className="form-section">
              <h2>Ingest Artifact - POST /artifact/{`{artifact_type}`}</h2>
              <div className="input-group">
                <label>Artifact Type:</label>
                <select
                  value={artifactType}
                  onChange={(e) => setArtifactType(e.target.value)}
                >
                  <option value="model">model</option>
                  <option value="dataset">dataset</option>
                  <option value="code">code</option>
                </select>
              </div>
              <div className="input-group">
                <label>URL:</label>
                <input
                  type="text"
                  placeholder="https://example.com/artifact"
                  value={artifactUrl}
                  onChange={(e) => setArtifactUrl(e.target.value)}
                />
              </div>
              <button
                className="submit-btn"
                onClick={handleIngestArtifact}
                disabled={loading}
              >
                {loading ? "Loading..." : "Ingest Artifact"}
              </button>
            </div>
          )}

          {/* Search by Regex Tab */}
          {activeTab === "search" && (
            <div className="form-section">
              <h2>Search by Regex - POST /artifact/byRegEx</h2>
              <div className="input-group">
                <label>Regex Pattern:</label>
                <input
                  type="text"
                  placeholder="e.g., .*model.*"
                  value={regexPattern}
                  onChange={(e) => setRegexPattern(e.target.value)}
                />
              </div>
              <button
                className="submit-btn"
                onClick={handleSearchByRegex}
                disabled={loading}
              >
                {loading ? "Loading..." : "Search"}
              </button>
            </div>
          )}

          {/* Get Artifact Tab */}
          {activeTab === "getArtifact" && (
            <div className="form-section">
              <h2>Get Artifact - GET /artifact/{`{artifact_type}`}/{`{id}`}</h2>
              <div className="input-group">
                <label>Artifact Type:</label>
                <select
                  value={getArtifactType}
                  onChange={(e) => setGetArtifactType(e.target.value)}
                >
                  <option value="model">model</option>
                  <option value="dataset">dataset</option>
                  <option value="code">code</option>
                </select>
              </div>
              <div className="input-group">
                <label>Artifact ID:</label>
                <input
                  type="text"
                  placeholder="e.g., 1"
                  value={getArtifactId}
                  onChange={(e) => setGetArtifactId(e.target.value)}
                />
              </div>
              <button
                className="submit-btn"
                onClick={handleGetArtifact}
                disabled={loading}
              >
                {loading ? "Loading..." : "Get Artifact"}
              </button>
            </div>
          )}

          {/* Get by Name Tab */}
          {activeTab === "getByName" && (
            <div className="form-section">
              <h2>Get Artifact by Name - GET /artifact/byName/{`{name}`}</h2>
              <div className="input-group">
                <label>Artifact Name:</label>
                <input
                  type="text"
                  placeholder="e.g., my-artifact"
                  value={getArtifactByName}
                  onChange={(e) => setGetArtifactByName(e.target.value)}
                />
              </div>
              <button
                className="submit-btn"
                onClick={handleGetArtifactByName}
                disabled={loading}
              >
                {loading ? "Loading..." : "Get Artifact"}
              </button>
            </div>
          )}

          {/* Get All Artifacts Tab */}
          {activeTab === "getAllArtifacts" && (
            <div className="form-section">
              <h2>Get All Artifacts - GET /artifact</h2>
              <p style={{ color: "#666", fontSize: "13px" }}>
                Fetch all artifacts from the database.
              </p>
              <button
                className="submit-btn"
                onClick={handleGetAllArtifacts}
                disabled={loading}
              >
                {loading ? "Loading..." : "Get All Artifacts"}
              </button>
            </div>
          )}

          {/* Utility Tab */}
          {activeTab === "utility" && (
            <div className="form-section">
              <h2>Utility Endpoints</h2>
              <div className="utility-buttons">
                <button
                  className="submit-btn"
                  onClick={handleHealthCheck}
                  disabled={loading}
                >
                  {loading ? "Loading..." : "Health Check"}
                </button>
                <button
                  className="submit-btn"
                  onClick={handleGetTracks}
                  disabled={loading}
                >
                  {loading ? "Loading..." : "Get Tracks"}
                </button>
                <button
                  className="submit-btn danger"
                  onClick={handleReset}
                  disabled={loading}
                >
                  {loading ? "Loading..." : "Reset System"}
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="output-section">
          <h3>Output Console</h3>
          <pre className="output-console">{output || "No output yet..."}</pre>
        </div>
      </div>
    </div>
  );
}
