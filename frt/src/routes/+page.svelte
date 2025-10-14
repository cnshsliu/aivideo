<script lang="ts">
  import { onMount } from 'svelte';
  import WelcomeScreen from '$lib/components/WelcomeScreen.svelte';
  import AppHeader from '$lib/components/AppHeader.svelte';
  import MediaPreviewModal from './MediaPreviewModal.svelte';
  import ProjectsTab from './ProjectsTab.svelte';
  import MediaTab from './MediaTab.svelte';
  import ProjectDetailsTab from './ProjectDetailsTab.svelte';
  import CreateProjectModal from './CreateProjectModal.svelte';
  import MaterialsModal from './MaterialsModal.svelte';
  import AuthModal from './AuthModal.svelte';

  interface User {
    id: string;
    username: string;
  }

  interface Project {
    id: string;
    name: string;
    title: string;
    video_title: string;
    createdAt: string;
    updatedAt: string;
    prompt?: string;
    staticSubtitle?: string;
  }

  let user = $state<User | null>(null);
  let showAuth = $state(false);
  let checkingAuth = $state(true);
  let error = $state('');
  let success = $state('');

  // Project management
  let projects = $state<Project[]>([]);
  let selectedProject = $state<Project | null>(null);
  let onUpdateProject = $state<(project: Project) => void>((project) => {
    selectedProject = project;
    const index = projects.findIndex((p) => p.name === project.name);
    if (index !== -1) {
      projects[index] = project;
    }
  });
  let showCreateProject = $state(false);
  let newProjectName = $state('');
  let newProjectTitle = $state('');

  // Media management
  let activeTab = $state('projects');
  let selectedFile = $state<File | null>(null);
  let uploadLevel = $state('public'); // 'public', 'user', 'project'
  let isUploading = $state(false);
  let mediaTabRef = $state<MediaTab | null>(null);

  // Materials management
  let showMaterialsModal = $state(false);
  let materialsTab = $state('public'); // 'public', 'user', 'project'
  let materialsCloseCallback = $state<(() => void) | undefined>(undefined);
  let previewMedia = $state<{
    type: 'image' | 'video';
    url: string;
    name: string;
    poster?: string;
  } | null>(null);

  // Video generation
  let generatingVideo = $state(false);
  let generationLogs = $state('');
  let showLogs = $state(false);
  let logPollingInterval = $state<NodeJS.Timeout | null>(null);

  onMount(async () => {
    await checkCurrentUser();
    await loadUserProjects();
  });

  // Cleanup polling when component is destroyed
  $effect(() => {
    return () => {
      stopLogPolling();
    };
  });

  async function checkCurrentUser() {
    try {
      const response = await fetch('/api/auth/user');
      if (response.ok) {
        user = await response.json();
        if (user) console.log('✅ User authenticated:', user.username);
        else console.log('ℹ️ No active session');
      } else if (response.status === 401) {
        user = null;
        console.log('ℹ️ No active session');
      }
    } catch (err) {
      user = null;
      console.error('Failed to check current user:', err);
    } finally {
      checkingAuth = false;
    }
  }

  async function loadUserProjects() {
    if (!user) return;

    try {
      console.log('🔄 Loading user projects...');
      const response = await fetch('/api/projects');
      if (response.ok) {
        projects = await response.json();
        console.log('✅ Projects loaded:', projects);
      } else {
        console.error(
          '❌ Failed to load projects:',
          response.status,
          await response.text()
        );
        if (response.status === 401) {
          console.log('🔐 Session expired, logging out...');
          user = null;
          projects = [];
          error = 'Session expired. Please login again.';
          setTimeout(() => (error = ''), 5000);
        }
      }
    } catch (err) {
      console.error('❌ Error loading projects:', err);
    }
  }

  async function handleLogin(event: Event) {
    event.preventDefault();
    const form = event.target as HTMLFormElement;
    const formData = new FormData(form);

    try {
      const response = await fetch('/api/auth', {
        method: 'POST',
        body: formData
      });

      const data = await response.json();

      if (response.ok && data.success) {
        await checkCurrentUser();
        await loadUserProjects();
        showAuth = false;

        if (data.action === 'register') {
          success =
            'Registration successful! Welcome to the video content service.';
        } else {
          success = 'Login successful!';
        }
        setTimeout(() => (success = ''), 3000);
      } else {
        if (data.action === 'login_failed') {
          error = 'Invalid username or password.';
        } else {
          error = data.message || 'Authentication failed';
        }
        setTimeout(() => (error = ''), 3000);
      }
    } catch (err: unknown) {
      error = 'Network error. Please try again.';
      setTimeout(() => (error = ''), 3000);
      console.log(err);
    }
  }

  async function handleLogout() {
    try {
      const response = await fetch('/api/auth/logout', { method: 'POST' });

      if (response.ok) {
        await checkCurrentUser();
        projects = [];
        selectedProject = null;
        success = 'Logged out successfully!';
        setTimeout(() => (success = ''), 3000);
      } else {
        const errorData = await response.json();
        error = errorData.message || 'Logout failed';
        setTimeout(() => (error = ''), 3000);
      }
    } catch (err: unknown) {
      error = 'Network error during logout';
      console.log(err);
      setTimeout(() => (error = ''), 3000);
    }
  }

  async function createProject() {
    if (!user || !newProjectName.trim()) return;

    try {
      const response = await fetch('/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newProjectName.trim(),
          title: newProjectTitle.trim() || newProjectName.trim()
        })
      });

      if (response.ok) {
        await loadUserProjects();
        showCreateProject = false;
        newProjectName = '';
        newProjectTitle = '';
        success = 'Project created successfully!';
        setTimeout(() => (success = ''), 3000);
      } else {
        const errorData = await response.json();
        error = errorData.message || 'Failed to create project';
        setTimeout(() => (error = ''), 3000);
      }
    } catch (err) {
      error = 'Network error';
      console.log(err);
      setTimeout(() => (error = ''), 3000);
    }
  }

  async function copyProject(project: Project, name?: string, title?: string) {
    try {
      const response = await fetch(`/api/projects/${project.id}/copy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, title })
      });

      if (response.ok) {
        await loadUserProjects();
        const newProject = await response.json();
        selectedProject = newProject;
        activeTab = 'project-details';
        success = 'Project copied successfully!';
        setTimeout(() => (success = ''), 3000);
      } else {
        error = 'Failed to copy project';
        setTimeout(() => (error = ''), 3000);
      }
    } catch (err) {
      error = 'Network error';
      console.log(err);
      setTimeout(() => (error = ''), 3000);
    }
  }

  async function deleteProject(projectId: string) {
    try {
      const response = await fetch(`/api/projects/${projectId}`, {
        method: 'DELETE'
      });

      if (response.ok) {
        await loadUserProjects();
        if (selectedProject?.id === projectId) {
          selectedProject = null;
        }
        success = 'Project deleted successfully!';
        setTimeout(() => (success = ''), 3000);
      } else {
        error = 'Failed to delete project';
        setTimeout(() => (error = ''), 3000);
      }
    } catch (err) {
      error = 'Network error';
      console.log(err);
      setTimeout(() => (error = ''), 3000);
    }
  }

  function selectProject(project: Project) {
    selectedProject = project;
    activeTab = 'project-details';
  }

  async function generateVideo() {
    if (!selectedProject) return;

    generatingVideo = true;
    generationLogs = '';
    showLogs = true;

    console.log(
      '🎬 Starting video generation for project:',
      selectedProject.id
    );

    // Start polling for log updates
    startLogPolling(selectedProject.id);

    try {
      const response = await fetch(
        `/api/projects/${selectedProject.id}/generate`,
        {
          method: 'POST'
        }
      );

      console.log('📡 Generate API response:', response.status);

      if (response.ok) {
        await response.json();
        // Handle video generation response
        success = 'Video generation started!';
        setTimeout(() => (success = ''), 3000);
      } else {
        const errorData = await response.json();
        error = errorData.message || 'Video generation failed';
        setTimeout(() => (error = ''), 3000);
      }
    } catch (err) {
      error = 'Network error during video generation';
      console.log(err);
      setTimeout(() => (error = ''), 3000);
    }

    // Don't stop polling immediately - let it run for a while to capture logs
    console.log(
      '⏳ Video generation API call completed, keeping polling active...'
    );

    // Stop polling after a reasonable timeout (e.g., 5 minutes)
    setTimeout(
      () => {
        console.log('⏰ Stopping log polling due to timeout');
        generatingVideo = false;
        stopLogPolling();
      },
      5 * 60 * 1000
    ); // 5 minutes
  }

  async function cancelVideoGeneration() {
    if (!selectedProject) return;

    console.log(
      '🛑 Cancelling video generation for project:',
      selectedProject.id
    );

    try {
      const response = await fetch(
        `/api/projects/${selectedProject.id}/generate`,
        {
          method: 'DELETE'
        }
      );

      console.log('📡 Cancel API response:', response.status);

      if (response.ok) {
        const data = await response.json();
        success = 'Cancelled';
        generatingVideo = false;
        stopLogPolling();
        setTimeout(() => (success = ''), 3000);
      } else {
        const errorData = await response.json();
        error = errorData.message || 'Failed to cancel video generation';
        setTimeout(() => (error = ''), 3000);
      }
    } catch (err) {
      error = 'Network error during cancellation';
      console.log(err);
      setTimeout(() => (error = ''), 3000);
    }
  }

  async function uploadMedia(options?: { level?: string; folderPath?: string }) {
    if (!selectedFile) return;

    isUploading = true;
    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('level', options?.level || uploadLevel);
      if (options?.folderPath) {
        formData.append('folderPath', options.folderPath);
      }
      console.log('=-======', options?.level || uploadLevel, options?.folderPath);

      const response = await fetch('/api/media/upload', {
        method: 'POST',
        body: formData
      });

      if (response.ok) {
        // Dispatch a custom event to notify MediaTab of successful upload
        window.dispatchEvent(
          new CustomEvent('mediaUploadComplete', {
            detail: { level: uploadLevel }
          })
        );

        await loadUserProjects(); // Refresh if needed
        success = 'Media uploaded successfully!';
        setTimeout(() => (success = ''), 3000);
        selectedFile = null;
      } else {
        const errorData = await response.json();
        error = errorData.message || 'Upload failed';
        setTimeout(() => (error = ''), 3000);
      }
    } catch (err) {
      error = 'Network error during upload';
      console.log(err);
      setTimeout(() => (error = ''), 3000);
    } finally {
      isUploading = false;
    }
  }

  // Function to fetch logs from the API
  async function fetchLogs(projectId: string): Promise<string> {
    try {
      const response = await fetch(`/api/projects/${projectId}/log`);
      console.log(response);
      if (response.ok) {
        return await response.text();
      } else {
        console.warn('Failed to fetch logs:', response.status);
        return generationLogs; // Return current logs if fetch fails
      }
    } catch (err) {
      console.error('Error fetching logs:', err);
      return generationLogs; // Return current logs if fetch fails
    }
  }

  // Function to fetch project status
  async function fetchProjectStatus(
    projectId: string
  ): Promise<{ progressStep: string; progressResult?: string }> {
    try {
      const response = await fetch(`/api/projects/${projectId}`);
      if (response.ok) {
        const project = await response.json();
        return {
          progressStep: project.progressStep || 'unknown',
          progressResult: project.progressResult
        };
      }
      return { progressStep: 'unknown' };
    } catch (err) {
      console.error('Error fetching project status:', err);
      return { progressStep: 'unknown' };
    }
  }

  // Function to start polling for log updates and status
  function startLogPolling(projectId: string) {
    console.log('🔄 Starting log polling for project:', projectId);
    // Clear any existing polling
    stopLogPolling();

    // Start polling every 2 seconds
    logPollingInterval = setInterval(async () => {
      console.log('📡 Polling for logs and status...');

      // Fetch logs
      const newLogs = await fetchLogs(projectId);
      if (newLogs !== generationLogs) {
        console.log('📝 Updating generationLogs');
        generationLogs = newLogs;
      }

      // Fetch project status
      const status = await fetchProjectStatus(projectId);
      console.log('📊 Project status:', status.progressStep);

      // Check if generation is complete
      if (
        status.progressStep === 'complete' ||
        status.progressStep === 'error'
      ) {
        console.log(
          '✅ Video generation completed with status:',
          status.progressStep
        );
        generatingVideo = false;
        stopLogPolling();

        if (status.progressStep === 'complete') {
          success = 'Video generation completed successfully!';
        } else {
          error = 'Video generation failed. Check logs for details.';
        }
        setTimeout(() => {
          success = '';
          error = '';
        }, 5000);
      }
    }, 2000);
  }

  // Function to stop polling for log updates
  function stopLogPolling() {
    if (logPollingInterval) {
      clearInterval(logPollingInterval);
      logPollingInterval = null;
    }
  }
</script>

<div class="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
  <AppHeader
    {checkingAuth}
    {user}
    onLogout={handleLogout}
    onShowAuth={() => (showAuth = true)}
  />

  <!-- Success/Error Messages -->
  {#if success}
    <div
      class="fixed top-20 right-4 z-50 animate-in slide-in-from-top-2 fade-in duration-300 rounded-lg border border-green-400 bg-green-100 p-3 text-green-700 shadow-lg max-w-xs"
    >
      <div class="flex items-center gap-2">
        <svg class="w-4 h-4 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
        </svg>
        <span class="text-sm font-medium">{success}</span>
      </div>
    </div>
  {/if}
  {#if error}
    <div
      class="fixed top-20 right-4 z-50 animate-in slide-in-from-top-2 fade-in duration-300 rounded-lg border border-red-400 bg-red-100 p-3 text-red-700 shadow-lg max-w-xs"
    >
      <div class="flex items-center gap-2">
        <svg class="w-4 h-4 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
        </svg>
        <span class="text-sm font-medium">{error}</span>
      </div>
    </div>
  {/if}

  <!-- Main Content -->
  <MediaPreviewModal {previewMedia} onClose={() => (previewMedia = null)} />

  {#if user}
    <!-- Main Tabs -->
    <div class="mb-6" id="main-tab">
      <div class="flex rounded-lg bg-gray-100/50 p-1">
        <button
          class="flex-1 rounded-md px-4 py-2 transition-all duration-200"
          class:bg-white={activeTab === 'projects'}
          class:text-gray-900={activeTab === 'projects'}
          class:text-gray-600={activeTab !== 'projects'}
          onclick={() => (activeTab = 'projects')}
        >
          Projects
        </button>
        <button
          class="flex-1 rounded-md px-4 py-2 transition-all duration-200"
          class:bg-white={activeTab === 'media'}
          class:text-gray-900={activeTab === 'media'}
          class:text-gray-600={activeTab !== 'media'}
          onclick={() => (activeTab = 'media')}
        >
          Media Library
        </button>
        {#if selectedProject}
          <button
            class="flex-1 rounded-md px-4 py-2 transition-all duration-200"
            class:bg-white={activeTab === 'project-details'}
            class:text-gray-900={activeTab === 'project-details'}
            class:text-gray-600={activeTab !== 'project-details'}
            onclick={() => (activeTab = 'project-details')}
          >
            Project Details
          </button>
        {/if}
      </div>
    </div>

    {#if activeTab === 'projects'}
      <ProjectsTab
        {projects}
        onSelectProject={selectProject}
        onCopyProject={copyProject}
        onDeleteProject={deleteProject}
        onCreateProject={() => (showCreateProject = true)}
      />
    {:else if activeTab === 'media'}
      <MediaTab
        bind:this={mediaTabRef}
        {selectedFile}
        bind:uploadLevel
        {selectedProject}
        {isUploading}
        onMediaSelect={(file: File) => (selectedFile = file)}
        onUpload={uploadMedia}
        onPreviewMedia={(media: {
          type: 'image' | 'video';
          url: string;
          name: string;
          poster?: string;
        }) => (previewMedia = media)}
        onMediaSelectionChange={() => {}}
        onMediaSelectionDone={() => {}}
      />
      level: {uploadLevel}
    {:else if activeTab === 'project-details' && selectedProject}
      <ProjectDetailsTab
        {selectedProject}
        {generatingVideo}
        {showLogs}
        {generationLogs}
        onGenerateVideo={generateVideo}
        onCancelVideo={cancelVideoGeneration}
        onShowMaterialsModal={(callback) => {
          showMaterialsModal = true;
          materialsCloseCallback = callback;
        }}
        {onUpdateProject}
        onPreviewMedia={(media) => (previewMedia = media)}
      />
    {/if}
  {:else}
    <WelcomeScreen onGetStarted={() => (showAuth = true)} />
  {/if}

  <!-- Create Project Modal -->
  <CreateProjectModal
    {showCreateProject}
    bind:newProjectName
    bind:newProjectTitle
    onCreateProject={createProject}
    onClose={() => {
      showCreateProject = false;
      newProjectName = '';
      newProjectTitle = '';
    }}
  />

  <!-- Authentication Modal -->
  <AuthModal
    {showAuth}
    onClose={() => (showAuth = false)}
    onLogin={handleLogin}
  />

  <!-- Materials Management Modal -->
  <MaterialsModal
    {showMaterialsModal}
    {materialsTab}
    {selectedProject}
    currentUsername={user?.username}
    onClose={() => {
      showMaterialsModal = false;
      if (materialsCloseCallback) {
        materialsCloseCallback();
        materialsCloseCallback = undefined;
      }
    }}
    onPreviewMedia={(media) => (previewMedia = media)}
  />
</div>
