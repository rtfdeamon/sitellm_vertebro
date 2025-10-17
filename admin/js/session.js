(function (global) {
  const PROJECT_STORAGE_KEY = 'admin_project';

  const sessionDefaults = {
    username: '',
    is_super: false,
    projects: [],
    primary_project: null,
    can_manage_projects: false,
  };

  const restoreStoredProject = () => {
    try {
      const stored = global.localStorage.getItem(PROJECT_STORAGE_KEY);
      return stored ? stored.trim().toLowerCase() : '';
    } catch (error) {
      console.warn('admin_project_restore_failed', error);
      return '';
    }
  };

  global.sessionDefaults = sessionDefaults;
  global.adminSession = { ...sessionDefaults };
  global.currentProject = restoreStoredProject();
  global.clusterAvailabilityTimer = null;
  global.promptAiHandlers = [];

  const AUTH_CANCELLED_ERROR = 'admin-auth-cancelled';

  async function fetchSession() {
    try {
      const resp = await fetch('/api/v1/admin/session');
      if (resp.status === 401) {
        throw new Error(AUTH_CANCELLED_ERROR);
      }
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      const normalize = typeof global.normalizeProjectName === 'function'
        ? global.normalizeProjectName
        : (value) => (typeof value === 'string' ? value.trim().toLowerCase() : '');
      const projects = Array.isArray(data.projects)
        ? data.projects.map((item) => normalize(item)).filter(Boolean)
        : [];
      global.adminSession = {
        username: typeof data.username === 'string' ? data.username.trim().toLowerCase() : '',
        is_super: Boolean(data.is_super),
        can_manage_projects: Boolean(data.can_manage_projects),
        projects,
        primary_project: data.primary_project ? normalize(data.primary_project) : (projects[0] || null),
      };
    } catch (error) {
      if (error && error.message !== AUTH_CANCELLED_ERROR) {
        console.error('Failed to load admin session', error);
      }
      global.adminSession = { ...sessionDefaults };
    }
    if (typeof global.applySessionPermissions === 'function') {
      global.applySessionPermissions();
    }
  }

  async function bootstrapAdminApp({
    refreshClusterAvailability,
    loadLlmModels,
    refreshOllamaCatalog,
    refreshOllamaServers,
    fetchProjectStorage,
    fetchProjects,
    loadProjectsList,
    loadRequestStats,
    fetchKnowledgeServiceStatus,
    fetchFeedbackTasks,
    populateProjectForm,
    loadKnowledge,
    pollStatus,
    updateProjectSummary,
  }) {
    await fetchSession();
    if (!global.adminSession.username) {
      const needAuth = typeof global.requestAdminAuth === 'function' ? await global.requestAdminAuth() : false;
      if (needAuth) {
        await fetchSession();
      }
    }
    if (typeof refreshClusterAvailability === 'function') {
      await refreshClusterAvailability();
    }
    if (!global.currentProject && global.adminSession.primary_project) {
      global.currentProject = global.adminSession.primary_project;
    }
    if (global.adminSession.is_super) {
      if (typeof refreshOllamaCatalog === 'function') {
        await refreshOllamaCatalog(true);
      }
      if (typeof refreshOllamaServers === 'function') {
        await refreshOllamaServers();
      }
      if (typeof loadLlmModels === 'function') {
        await loadLlmModels();
      }
    } else if (typeof loadLlmModels === 'function') {
      await loadLlmModels();
    }
    if (typeof fetchProjectStorage === 'function') {
      await fetchProjectStorage();
    }
    if (typeof fetchProjects === 'function') {
      await fetchProjects();
    }
    if (typeof loadProjectsList === 'function') {
      await loadProjectsList();
    }
    if (typeof fetchProjectStorage === 'function') {
      await fetchProjectStorage();
    }
    if (typeof loadRequestStats === 'function') {
      await loadRequestStats();
    }
    if (global.adminSession.is_super) {
      if (typeof fetchKnowledgeServiceStatus === 'function') {
        await fetchKnowledgeServiceStatus();
      }
      if (typeof fetchFeedbackTasks === 'function') {
        await fetchFeedbackTasks();
      }
    }
    if (global.currentProject) {
      if (typeof populateProjectForm === 'function') {
        populateProjectForm(global.currentProject);
      }
      if (typeof loadKnowledge === 'function') {
        await loadKnowledge();
      }
      if (typeof pollStatus === 'function') {
        pollStatus();
      }
    } else if (typeof updateProjectSummary === 'function') {
      updateProjectSummary();
    }
    if (!global.clusterAvailabilityTimer && typeof refreshClusterAvailability === 'function') {
      global.clusterAvailabilityTimer = setInterval(() => {
        refreshClusterAvailability();
      }, 20000);
    }
  }

  global.fetchSession = fetchSession;
  global.bootstrapAdminApp = bootstrapAdminApp;

  global.addEventListener('beforeunload', () => {
    (global.promptAiHandlers || []).forEach((handler) => {
      if (handler && typeof handler.abort === 'function') {
        try {
          handler.abort();
        } catch (error) {
          console.warn('prompt_ai_abort_failed', error);
        }
      }
    });
    if (global.clusterAvailabilityTimer) {
      clearInterval(global.clusterAvailabilityTimer);
      global.clusterAvailabilityTimer = null;
    }
    if (global.healthPollTimer) {
      clearInterval(global.healthPollTimer);
      global.healthPollTimer = null;
    }
  });
})(window);
