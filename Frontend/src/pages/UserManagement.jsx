import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import api from "../services/apiClient";
import "./UserManagement.css";

export default function UserManagement() {
  const { user, logout, isAdmin } = useAuth();
  const navigate = useNavigate();
  
  // State management
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [deleteInProgress, setDeleteInProgress] = useState(null);
  const [editingUser, setEditingUser] = useState(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  
  // Form state
  const [formData, setFormData] = useState({
    username: "",
    email: "",
    password: "",
    role: "user",
  });
  
  // Refs for accessibility
  const statusMessageRef = useRef(null);
  const createFormRef = useRef(null);
  const editFormRef = useRef(null);

  // Redirect if not admin
  useEffect(() => {
    if (!isAdmin()) {
      navigate("/dashboard");
    }
  }, [isAdmin, navigate]);

  // Fetch users on mount
  useEffect(() => {
    fetchUsers();
  }, []);

  // Focus form when opened
  useEffect(() => {
    if (showCreateForm && createFormRef.current) {
      createFormRef.current.querySelector('input').focus();
    }
  }, [showCreateForm]);

  useEffect(() => {
    if (editingUser && editFormRef.current) {
      editFormRef.current.querySelector('input').focus();
    }
  }, [editingUser]);

  const fetchUsers = async () => {
    setLoading(true);
    setError("");
    try {
      const { data } = await api.get("/auth/users");
      setUsers(data);
      announceStatus(`Loaded ${data.length} users`);
    } catch (err) {
      const message = err.response?.data?.detail || "Failed to load users";
      setError(message);
      announceStatus(`Error: ${message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    setError("");
    setSuccessMessage("");
    
    try {
      await api.post("/auth/register", formData);
      setSuccessMessage(`User ${formData.username} created successfully`);
      announceStatus(`User ${formData.username} created successfully`);
      setFormData({ username: "", email: "", password: "", role: "user" });
      setShowCreateForm(false);
      fetchUsers();
    } catch (err) {
      const message = err.response?.data?.detail || "Failed to create user";
      setError(message);
      announceStatus(`Error: ${message}`);
    }
  };

  const handleUpdateUser = async (e) => {
    e.preventDefault();
    setError("");
    setSuccessMessage("");
    
    const updateData = {};
    if (formData.email) updateData.email = formData.email;
    if (formData.role) updateData.role = formData.role;
    if (formData.password) updateData.password = formData.password;
    
    try {
      await api.put(`/auth/users/${editingUser.username}`, updateData);
      setSuccessMessage(`User ${editingUser.username} updated successfully`);
      announceStatus(`User ${editingUser.username} updated successfully`);
      setEditingUser(null);
      setFormData({ username: "", email: "", password: "", role: "user" });
      fetchUsers();
    } catch (err) {
      const message = err.response?.data?.detail || "Failed to update user";
      setError(message);
      announceStatus(`Error: ${message}`);
    }
  };

  const handleDeleteUser = async (username) => {
    if (!window.confirm(`Are you sure you want to delete user "${username}"?`)) {
      return;
    }

    setDeleteInProgress(username);
    setError("");
    setSuccessMessage("");
    
    try {
      await api.delete(`/auth/users/${username}`);
      setSuccessMessage(`User ${username} deleted successfully`);
      announceStatus(`User ${username} deleted successfully`);
      fetchUsers();
    } catch (err) {
      const message = err.response?.data?.detail || "Failed to delete user";
      setError(message);
      announceStatus(`Error: ${message}`);
    } finally {
      setDeleteInProgress(null);
    }
  };

  const startEdit = (user) => {
    setEditingUser(user);
    setFormData({
      username: user.username,
      email: user.email,
      password: "",
      role: user.role,
    });
    setShowCreateForm(false);
  };

  const cancelEdit = () => {
    setEditingUser(null);
    setFormData({ username: "", email: "", password: "", role: "user" });
  };

  const cancelCreate = () => {
    setShowCreateForm(false);
    setFormData({ username: "", email: "", password: "", role: "user" });
  };

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const announceStatus = (message) => {
    if (statusMessageRef.current) {
      statusMessageRef.current.textContent = message;
    }
  };

  return (
    <div className="user-management">
      {/* Screen reader status announcements */}
      <div
        ref={statusMessageRef}
        className="sr-only"
        role="status"
        aria-live="polite"
        aria-atomic="true"
      />

      {/* Header */}
      <header className="user-management-header">
        <div className="header-content">
          <h1 id="user-management-title">
            <span className="logo" aria-label="ACME">🏢</span>
            User Management
          </h1>
          <div className="user-info">
            <span className="user-welcome" aria-label={`Logged in as ${user?.username}`}>
              <span className="user-icon" aria-hidden="true">👤</span>
              <strong>{user?.username}</strong>
              <span className="admin-badge" aria-label="Administrator">Admin</span>
            </span>
            <button
              onClick={() => navigate("/dashboard")}
              className="btn btn-secondary"
              aria-label="Back to Dashboard"
            >
              ← Dashboard
            </button>
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

      <main className="user-management-main" role="main" aria-labelledby="user-management-title">
        {/* Actions Bar */}
        <section className="actions-bar" aria-label="User actions">
          <button
            onClick={() => {
              setShowCreateForm(true);
              setEditingUser(null);
            }}
            className="btn btn-primary"
            aria-label="Create new user"
            disabled={showCreateForm || editingUser}
          >
            <span aria-hidden="true">➕</span> Create User
          </button>
        </section>

        {/* Success/Error Messages */}
        {successMessage && (
          <div className="success-banner" role="alert" aria-live="polite">
            <strong>Success:</strong> {successMessage}
            <button
              onClick={() => setSuccessMessage("")}
              className="message-close"
              aria-label="Dismiss success message"
            >
              ×
            </button>
          </div>
        )}

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

        {/* Create User Form */}
        {showCreateForm && (
          <section className="user-form-section" aria-labelledby="create-user-title">
            <form ref={createFormRef} onSubmit={handleCreateUser} className="user-form">
              <h2 id="create-user-title">Create New User</h2>
              
              <div className="form-group">
                <label htmlFor="create-username">
                  Username <span aria-label="required">*</span>
                </label>
                <input
                  id="create-username"
                  type="text"
                  value={formData.username}
                  onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                  required
                  minLength={3}
                  maxLength={50}
                  aria-required="true"
                />
              </div>

              <div className="form-group">
                <label htmlFor="create-email">
                  Email <span aria-label="required">*</span>
                </label>
                <input
                  id="create-email"
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  required
                  aria-required="true"
                />
              </div>

              <div className="form-group">
                <label htmlFor="create-password">
                  Password <span aria-label="required">*</span>
                </label>
                <input
                  id="create-password"
                  type="password"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  required
                  minLength={6}
                  aria-required="true"
                />
              </div>

              <div className="form-group">
                <label htmlFor="create-role">Role</label>
                <select
                  id="create-role"
                  value={formData.role}
                  onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                >
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                </select>
              </div>

              <div className="form-actions">
                <button type="submit" className="btn btn-primary">
                  Create User
                </button>
                <button type="button" onClick={cancelCreate} className="btn btn-secondary">
                  Cancel
                </button>
              </div>
            </form>
          </section>
        )}

        {/* Edit User Form */}
        {editingUser && (
          <section className="user-form-section" aria-labelledby="edit-user-title">
            <form ref={editFormRef} onSubmit={handleUpdateUser} className="user-form">
              <h2 id="edit-user-title">Edit User: {editingUser.username}</h2>
              
              <div className="form-group">
                <label htmlFor="edit-email">Email</label>
                <input
                  id="edit-email"
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  placeholder="Leave empty to keep current"
                />
              </div>

              <div className="form-group">
                <label htmlFor="edit-password">
                  New Password
                </label>
                <input
                  id="edit-password"
                  type="password"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  placeholder="Leave empty to keep current"
                  minLength={6}
                />
                <small className="form-hint">Leave empty to keep current password</small>
              </div>

              <div className="form-group">
                <label htmlFor="edit-role">Role</label>
                <select
                  id="edit-role"
                  value={formData.role}
                  onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                >
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                </select>
              </div>

              <div className="form-actions">
                <button type="submit" className="btn btn-primary">
                  Update User
                </button>
                <button type="button" onClick={cancelEdit} className="btn btn-secondary">
                  Cancel
                </button>
              </div>
            </form>
          </section>
        )}

        {/* Users List */}
        <section className="users-section" aria-labelledby="users-title">
          <h2 id="users-title">
            Users
            {!loading && (
              <span className="users-count" aria-label={`${users.length} users`}>
                ({users.length})
              </span>
            )}
          </h2>

          {loading ? (
            <div className="loading-state" role="status" aria-live="polite">
              <div className="spinner" aria-hidden="true"></div>
              <p>Loading users...</p>
            </div>
          ) : users.length === 0 ? (
            <div className="empty-state" role="status">
              <p>No users found.</p>
            </div>
          ) : (
            <div className="users-table-container">
              <table className="users-table" role="table">
                <thead>
                  <tr>
                    <th scope="col">Username</th>
                    <th scope="col">Email</th>
                    <th scope="col">Role</th>
                    <th scope="col">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.username}>
                      <td data-label="Username">
                        <strong>{u.username}</strong>
                      </td>
                      <td data-label="Email">{u.email}</td>
                      <td data-label="Role">
                        <span className={`role-badge role-${u.role}`}>
                          {u.role}
                        </span>
                      </td>
                      <td data-label="Actions">
                        <div className="action-buttons">
                          <button
                            onClick={() => startEdit(u)}
                            className="btn btn-sm btn-secondary"
                            aria-label={`Edit ${u.username}`}
                            disabled={editingUser || showCreateForm}
                          >
                            <span aria-hidden="true">✏️</span> Edit
                          </button>
                          
                          {u.username !== "admin" && (
                            <button
                              onClick={() => handleDeleteUser(u.username)}
                              className="btn btn-sm btn-danger"
                              disabled={deleteInProgress === u.username}
                              aria-label={`Delete ${u.username}`}
                            >
                              {deleteInProgress === u.username ? (
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
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
