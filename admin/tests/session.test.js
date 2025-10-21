import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

const loadSessionModule = async () => {
  vi.resetModules();
  await import('../js/session.js');
};

const createFetchResponse = (body, { ok = true, status = 200 } = {}) => ({
  ok,
  status,
  json: async () => body,
});

describe('admin session', () => {
  beforeEach(() => {
    vi.stubGlobal('applySessionPermissions', vi.fn());
    window.localStorage.clear();
    window.sessionStorage.clear();
    window.clusterAvailabilityTimer = null;
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('fetchSession обновляет adminSession при успешном ответе', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      createFetchResponse({
        username: 'Admin ',
        is_super: true,
        can_manage_projects: true,
        projects: [' Demo ', 'Secondary'],
        primary_project: 'Demo',
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    await loadSessionModule();
    await window.fetchSession();

    expect(fetchMock).toHaveBeenCalledWith('/api/v1/admin/session');
    expect(window.adminSession.username).toBe('admin');
    expect(window.adminSession.is_super).toBe(true);
    expect(window.adminSession.can_manage_projects).toBe(true);
    expect(window.adminSession.projects).toEqual(['demo', 'secondary']);
    expect(window.adminSession.primary_project).toBe('demo');
    expect(window.applySessionPermissions).toHaveBeenCalledTimes(1);
  });

  it('fetchSession сбрасывает состояние при ошибке', async () => {
    const fetchMock = vi.fn().mockRejectedValue(new Error('network'));
    vi.stubGlobal('fetch', fetchMock);

    await loadSessionModule();
    window.adminSession.username = 'other';

    await window.fetchSession();

    expect(window.adminSession).toMatchObject({
      username: '',
      is_super: false,
      can_manage_projects: false,
      projects: [],
      primary_project: null,
    });
    expect(window.applySessionPermissions).toHaveBeenCalledTimes(1);
  });

  it('bootstrapAdminApp выполняет сценарий для супер-админа', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      createFetchResponse({
        username: 'Root',
        is_super: true,
        can_manage_projects: true,
        projects: ['demo'],
        primary_project: 'demo',
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    await loadSessionModule();
    window.currentProject = '';

    const refreshClusterAvailability = vi.fn().mockResolvedValue();
    const refreshOllamaCatalog = vi.fn().mockResolvedValue();
    const refreshOllamaServers = vi.fn().mockResolvedValue();
    const renderOllamaCatalogFromCache = vi.fn();
    const renderOllamaServersFromCache = vi.fn();
    const fetchProjectStorage = vi.fn().mockResolvedValue();
    const fetchProjects = vi.fn().mockResolvedValue();
    const loadProjectsList = vi.fn().mockResolvedValue();
    const loadRequestStats = vi.fn().mockResolvedValue();
    const fetchKnowledgeServiceStatus = vi.fn().mockResolvedValue();
    const fetchFeedbackTasks = vi.fn().mockResolvedValue();
    const populateProjectForm = vi.fn();
    const loadKnowledge = vi.fn().mockResolvedValue();
    const pollStatus = vi.fn();
    const updateProjectSummary = vi.fn();
    const loadLlmModels = vi.fn();
    const setIntervalSpy = vi.spyOn(global, 'setInterval').mockImplementation(() => 42);

    await window.bootstrapAdminApp({
      refreshClusterAvailability,
      loadLlmModels,
      refreshOllamaCatalog,
      refreshOllamaServers,
      renderOllamaCatalogFromCache,
      renderOllamaServersFromCache,
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
    });

    expect(refreshClusterAvailability).toHaveBeenCalledTimes(1);
    expect(refreshOllamaCatalog).toHaveBeenCalledWith(true);
    expect(refreshOllamaServers).toHaveBeenCalledTimes(1);
    expect(loadLlmModels).toHaveBeenCalledTimes(1);
    expect(fetchProjectStorage).toHaveBeenCalledTimes(2);
    expect(fetchProjects).toHaveBeenCalledTimes(1);
    expect(loadProjectsList).toHaveBeenCalledTimes(1);
    expect(loadRequestStats).toHaveBeenCalledTimes(1);
    expect(fetchKnowledgeServiceStatus).toHaveBeenCalledTimes(1);
    expect(fetchFeedbackTasks).toHaveBeenCalledTimes(1);
    expect(populateProjectForm).toHaveBeenCalledWith('demo');
    expect(loadKnowledge).toHaveBeenCalledTimes(1);
    expect(pollStatus).toHaveBeenCalledTimes(1);
    expect(updateProjectSummary).not.toHaveBeenCalled();
    expect(renderOllamaCatalogFromCache).not.toHaveBeenCalled();
    expect(renderOllamaServersFromCache).not.toHaveBeenCalled();
    expect(window.currentProject).toBe('demo');
    expect(window.clusterAvailabilityTimer).toBe(42);
    expect(setIntervalSpy).toHaveBeenCalledWith(expect.any(Function), 20000);
  });

  it('bootstrapAdminApp запускает сценарий для обычного администратора без проекта', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      createFetchResponse({
        username: 'Operator',
        is_super: false,
        can_manage_projects: true,
        projects: ['alpha'],
        primary_project: null,
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    await loadSessionModule();
    window.currentProject = '';

    const refreshClusterAvailability = vi.fn().mockResolvedValue();
    const refreshOllamaCatalog = vi.fn();
    const refreshOllamaServers = vi.fn();
    const renderOllamaCatalogFromCache = vi.fn();
    const renderOllamaServersFromCache = vi.fn();
    const fetchProjectStorage = vi.fn().mockResolvedValue();
    const fetchProjects = vi.fn().mockResolvedValue();
    const loadProjectsList = vi.fn().mockResolvedValue();
    const loadRequestStats = vi.fn().mockResolvedValue();
    const fetchKnowledgeServiceStatus = vi.fn();
    const fetchFeedbackTasks = vi.fn();
    const populateProjectForm = vi.fn();
    const loadKnowledge = vi.fn();
    const pollStatus = vi.fn();
    const updateProjectSummary = vi.fn();
    const loadLlmModels = vi.fn().mockResolvedValue();
    vi.spyOn(global, 'setInterval').mockImplementation(() => 101);

    await window.bootstrapAdminApp({
      refreshClusterAvailability,
      loadLlmModels,
      refreshOllamaCatalog,
      refreshOllamaServers,
      renderOllamaCatalogFromCache,
      renderOllamaServersFromCache,
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
    });

    expect(refreshClusterAvailability).toHaveBeenCalledTimes(1);
    expect(refreshOllamaCatalog).not.toHaveBeenCalled();
    expect(refreshOllamaServers).not.toHaveBeenCalled();
    expect(loadLlmModels).toHaveBeenCalledTimes(1);
    expect(fetchProjectStorage).toHaveBeenCalledTimes(2);
    expect(fetchProjects).toHaveBeenCalledTimes(1);
    expect(loadProjectsList).toHaveBeenCalledTimes(1);
    expect(loadRequestStats).toHaveBeenCalledTimes(1);
    expect(fetchKnowledgeServiceStatus).not.toHaveBeenCalled();
    expect(fetchFeedbackTasks).not.toHaveBeenCalled();
    expect(populateProjectForm).toHaveBeenCalledWith('alpha');
    expect(loadKnowledge).toHaveBeenCalledTimes(1);
    expect(pollStatus).toHaveBeenCalledTimes(1);
    expect(updateProjectSummary).not.toHaveBeenCalled();
    expect(renderOllamaCatalogFromCache).toHaveBeenCalledTimes(1);
    expect(renderOllamaServersFromCache).toHaveBeenCalledTimes(1);
  });
});
