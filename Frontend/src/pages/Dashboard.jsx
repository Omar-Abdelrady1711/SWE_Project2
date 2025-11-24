import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import api from "../services/apiClient";
import "./Dashboard.css";

export default function Dashboard() {
  const { user, logout, isAdmin } = useAuth();
  const navigate = useNavigate();
  
  // State management
  const [artifacts, setArtifacts] = useState([]);
  const [filteredArtifacts, setFilteredArtifacts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchMode, setSearchMode] = useState("client"); // client or server
  const [health, setHealth] = useState(null);
  const [deleteInProgress, setDeleteInProgress] = useState(null);
  
  // Refs for accessibility
  const searchInputRef = useRef(null);
  const statusMessageRef = useRef(null);

  // Fetch artifacts on mount
  useEffect(() => {
    fetchArtifacts();
    fetchHealth();
    // Refresh health metrics every 30 seconds
    const interval = setInterval(fetchHealth, 30000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Client-side filtering
  useEffect(() => {
    if (searchMode === "client") {
      if (!searchQuery.trim()) {
        setFilteredArtifacts(artifacts);
      } else {
        const query = searchQuery.toLowerCase();
        const filtered = artifacts.filter(
          (a) =>
            a.name.toLowerCase().includes(query) ||
            a.type.toLowerCase().includes(query) ||
            a.id.includes(query)
        );
        setFilteredArtifacts(filtered);
      }
    }
  }, [searchQuery, artifacts, searchMode]);

  const fetchArtifacts = async () => {
    setLoading(true);
    setError("");
    try {
      const { data } = await api.get("/artifact");
      setArtifacts(data);
      setFilteredArtifacts(data);
      announceStatus(`Loaded ${data.length} artifacts`);
    } catch (err) {
      const message = err.response?.data?.detail || "Failed to load artifacts";
      setError(message);
      announceStatus(`Error: ${message}`);
    } finally {
      setLoading(false);
    }
  };

  const fetchHealth = async () => {
    try {
      const { data } = await api.get("/health");
      setHealth(data.metrics);
    } catch (err) {
      console.error("Failed to fetch health metrics:", err);
    }
  };

  const handleServerSearch = async () => {
    if (!searchQuery.trim()) {
      fetchArtifacts();
      return;
    }

    setLoading(true);
    setError("");
    try {
      console.log('Sending regex search:', searchQuery);
      const { data } = await api.post("/artifact/byRegEx", {
        regex: searchQuery,
      });
      console.log('Regex search results:', data);
      setFilteredArtifacts(data);
      announceStatus(`Found ${data.length} matching artifacts`);
    } catch (err) {
      console.error('Regex search error:', err.response?.data);
      if (err.response?.status === 404) {
        setFilteredArtifacts([]);
        announceStatus("No artifacts found matching your search");
      } else {
        // Handle validation errors (422) and other errors
        let message = "Search failed";
        if (err.response?.data?.detail) {
          // Handle both string and array/object detail formats
          const detail = err.response.data.detail;
          if (typeof detail === 'string') {
            message = detail;
          } else if (Array.isArray(detail)) {
            message = detail.map(e => e.msg || e).join(', ');
          } else if (detail.msg) {
            message = detail.msg;
          }
        }
        setError(message);
        announceStatus(`Error: ${message}`);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (artifact) => {
    if (!window.confirm(`Are you sure you want to delete "${artifact.name}"?`)) {
      return;
    }

    setDeleteInProgress(artifact.id);
    try {
      await api.delete(`/artifact/${artifact.type}/${artifact.id}`);
      announceStatus(`Deleted ${artifact.name}`);
      fetchArtifacts(); // Refresh list
    } catch (err) {
      const message = err.response?.data?.detail || "Failed to delete artifact";
      setError(message);
      announceStatus(`Error: ${message}`);
    } finally {
      setDeleteInProgress(null);
    }
  };

  const handleViewDetails = (artifact) => {
    if (artifact.url) {
      // Open the artifact's URL in a new tab
      window.open(artifact.url, '_blank', 'noopener,noreferrer');
    } else {
      // Fallback to internal route if no URL
      navigate(`/artifact/${artifact.type}/${artifact.id}`);
    }
  };

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  // Screen reader announcements
  const announceStatus = (message) => {
    if (statusMessageRef.current) {
      statusMessageRef.current.textContent = message;
    }
  };

  return (
    <div className="dashboard">
      {/* Screen reader status announcements */}
      <div
        ref={statusMessageRef}
        className="sr-only"
        role="status"
        aria-live="polite"
        aria-atomic="true"
      />

      {/* Header */}
      <header className="dashboard-header">
        <div className="dashboard-header-content">
          <h1 id="dashboard-title">
            <span className="logo" aria-label="ACME">🏢</span>
            Model Registry Dashboard
          </h1>
          <div className="user-info">
            <span className="user-welcome" aria-label={`Logged in as ${user?.username}`}>
              <span className="user-icon" aria-hidden="true">👤</span>
              <strong>{user?.username}</strong>
              {user?.role === "admin" && (
                <span className="admin-badge" aria-label="Administrator">
                  Admin
                </span>
              )}
            </span>
            <button
              onClick={handleLogout}
              className="btn btn-secondary"
              aria-label="Log out"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      <main className="dashboard-main" role="main" aria-labelledby="dashboard-title">
        {/* Health Metrics Panel */}
        {health && (
          <section className="metrics-panel" aria-labelledby="metrics-title">
            <h2 id="metrics-title" className="sr-only">System Metrics</h2>
            <div className="metrics-grid">
              <div className="metric-card">
                <div className="metric-icon" aria-hidden="true">⏱️</div>
                <div className="metric-content">
                  <div className="metric-label">Uptime</div>
                  <div className="metric-value">{health.uptime_formatted}</div>
                </div>
              </div>
              <div className="metric-card">
                <div className="metric-icon" aria-hidden="true">📦</div>
                <div className="metric-content">
                  <div className="metric-label">Total Artifacts</div>
                  <div className="metric-value">{health.artifact_count}</div>
                </div>
              </div>
              <div className="metric-card">
                <div className="metric-icon" aria-hidden="true">⬆️</div>
                <div className="metric-content">
                  <div className="metric-label">Uploads</div>
                  <div className="metric-value">{health.upload_count}</div>
                </div>
              </div>
              <div className="metric-card">
                <div className="metric-icon" aria-hidden="true">📊</div>
                <div className="metric-content">
                  <div className="metric-label">Requests</div>
                  <div className="metric-value">
                    {health.total_requests}
                    <small className="metric-sublabel">
                      {health.request_rate}/s
                    </small>
                  </div>
                </div>
              </div>
              <div className="metric-card">
                <div className="metric-icon" aria-hidden="true">
                  {health.error_rate > 5 ? "⚠️" : "✅"}
                </div>
                <div className="metric-content">
                  <div className="metric-label">Error Rate</div>
                  <div className="metric-value">
                    {health.error_rate}%
                    <small className="metric-sublabel">
                      {health.error_count} errors
                    </small>
                  </div>
                </div>
              </div>
            </div>
          </section>
        )}

        {/* Actions Bar */}
        <section className="actions-bar" aria-label="Search and actions">
          <div className="search-container">
            <label htmlFor="search-input" className="sr-only">
              Search artifacts
            </label>
            <input
              ref={searchInputRef}
              id="search-input"
              type="search"
              className="search-input"
              placeholder="Search by name, type, or ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && searchMode === "server") {
                  handleServerSearch();
                }
              }}
              aria-describedby="search-mode-desc"
            />
            
            <div className="search-mode" id="search-mode-desc">
              <label>
                <input
                  type="radio"
                  name="searchMode"
                  value="client"
                  checked={searchMode === "client"}
                  onChange={(e) => setSearchMode(e.target.value)}
                />
                <span>Instant Filter</span>
              </label>
              <label>
                <input
                  type="radio"
                  name="searchMode"
                  value="server"
                  checked={searchMode === "server"}
                  onChange={(e) => setSearchMode(e.target.value)}
                />
                <span>Regex Search</span>
              </label>
              {searchMode === "server" && (
                <button
                  onClick={handleServerSearch}
                  className="btn btn-primary btn-sm"
                  disabled={loading}
                >
                  Search
                </button>
              )}
            </div>
          </div>

          <button
            onClick={() => navigate("/upload")}
            className="btn btn-primary"
            aria-label="Upload new artifact"
          >
            <span aria-hidden="true">⬆️</span> Upload Artifact
          </button>
        </section>

        {/* Error Display */}
        {error && (
          <div className="error-banner" role="alert" aria-live="assertive">
            <strong>Error:</strong> {error}
            <button
              onClick={() => setError("")}
              className="error-close"
              aria-label="Dismiss error"
            >
              ×
            </button>
          </div>
        )}

        {/* Artifacts List */}
        <section className="artifacts-section" aria-labelledby="artifacts-title">
          <h2 id="artifacts-title">
            Artifacts
            {!loading && (
              <span className="artifacts-count" aria-label={`${filteredArtifacts.length} artifacts`}>
                ({filteredArtifacts.length})
              </span>
            )}
          </h2>

          {loading ? (
            <div className="loading-state" role="status" aria-live="polite">
              <div className="spinner" aria-hidden="true"></div>
              <p>Loading artifacts...</p>
            </div>
          ) : filteredArtifacts.length === 0 ? (
            <div className="empty-state" role="status">
              <p>
                {searchQuery
                  ? "No artifacts found matching your search."
                  : "No artifacts available. Upload one to get started!"}
              </p>
            </div>
          ) : (
            <div className="artifacts-grid" role="list">
              {filteredArtifacts.map((artifact) => (
                <article
                  key={artifact.id}
                  className="artifact-card"
                  role="listitem"
                >
                  <div className="artifact-header">
                    <h3 className="artifact-name">{artifact.name}</h3>
                    <span className={`artifact-type type-${artifact.type}`}>
                      {artifact.type}
                    </span>
                  </div>
                  
                  <div className="artifact-meta">
                    <span className="artifact-id">ID: {artifact.id}</span>
                  </div>

                  <div className="artifact-actions">
                    <button
                      onClick={() => handleViewDetails(artifact)}
                      className="btn btn-secondary btn-sm"
                      aria-label={`View details for ${artifact.name}`}
                    >
                      <span aria-hidden="true">👁️</span> View
                    </button>
                    
                    {isAdmin() && (
                      <button
                        onClick={() => handleDelete(artifact)}
                        className="btn btn-danger btn-sm"
                        disabled={deleteInProgress === artifact.id}
                        aria-label={`Delete ${artifact.name}`}
                      >
                        {deleteInProgress === artifact.id ? (
                          <>
                            <span className="spinner-sm" aria-hidden="true"></span>
                            Deleting...
                          </>
                        ) : (
                          <>
                            <span aria-hidden="true">🗑️</span> Delete
                          </>
                        )}
                      </button>
                    )}
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
