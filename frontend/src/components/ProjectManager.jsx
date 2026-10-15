import React, { useState, useEffect, useCallback } from "react";
import { saveProject, listProjects, getProject } from "../api/client.js";

export default function ProjectManager({ currentCase, onProjectLoaded, onNotify }) {
  const [projectId, setProjectId] = useState("");
  const [savedProjects, setSavedProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState("");
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");

  const refreshList = useCallback(async () => {
    try {
      const res = await listProjects();
      const list = res.projects || [];
      setSavedProjects(list);
      if (list.length > 0 && !selectedProject) {
        setSelectedProject(list[0]);
      }
    } catch {
      // ignore network errors on init
    }
  }, [selectedProject]);

  useEffect(() => {
    refreshList();
  }, [refreshList]);

  const handleSave = async (e) => {
    e.preventDefault();
    if (!currentCase) return;
    setLoading(true);
    setMsg("");
    try {
      const res = await saveProject(currentCase, projectId.trim());
      const savedId = res.project_id;
      setMsg(`Project saved successfully (ID: ${savedId})`);
      if (onNotify) onNotify(`Project '${savedId}' saved`);
      await refreshList();
      setSelectedProject(savedId);
      setProjectId("");
    } catch (err) {
      setMsg(`Failed to save: ${err.message || "Unknown error"}`);
    } finally {
      setLoading(false);
    }
  };

  const handleLoad = async (e) => {
    e.preventDefault();
    if (!selectedProject) return;
    setLoading(true);
    setMsg("");
    try {
      const loadedCase = await getProject(selectedProject);
      if (onProjectLoaded) onProjectLoaded(loadedCase);
      setMsg(`Loaded project '${selectedProject}'`);
      if (onNotify) onNotify(`Project '${selectedProject}' loaded`);
    } catch (err) {
      setMsg(`Failed to load project: ${err.message || "Unknown error"}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <fieldset className="project-bar">
      <legend>Project Storage (Persistent Server JSON)</legend>
      <form onSubmit={handleSave} className="project-group">
        <label htmlFor="save-project-id">Save current case as ID / Name:</label>
        <div className="inputwrap">
          <input
            id="save-project-id"
            type="text"
            placeholder="e.g. project-01 (leave blank for auto)"
            value={projectId}
            onChange={(e) => setProjectId(e.target.value.replace(/[^a-zA-Z0-9_-]/g, ""))}
            disabled={loading}
          />
          <button type="submit" disabled={loading || !currentCase} className="btn-secondary">
            Save Project
          </button>
        </div>
      </form>

      <form onSubmit={handleLoad} className="project-group">
        <label htmlFor="open-project-select">Open saved project:</label>
        <div className="inputwrap">
          <select
            id="open-project-select"
            value={selectedProject}
            onChange={(e) => setSelectedProject(e.target.value)}
            disabled={loading || savedProjects.length === 0}
          >
            {savedProjects.length === 0 ? (
              <option value="">(No saved projects found)</option>
            ) : (
              savedProjects.map((pid) => (
                <option key={pid} value={pid}>
                  {pid}
                </option>
              ))
            )}
          </select>
          <button
            type="submit"
            disabled={loading || !selectedProject}
            className="btn-secondary"
          >
            Load Project
          </button>
        </div>
      </form>

      {msg && (
        <div className="project-status" role="status" aria-live="polite">
          {msg}
        </div>
      )}
    </fieldset>
  );
}
