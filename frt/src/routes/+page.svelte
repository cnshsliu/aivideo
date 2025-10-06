<script lang="ts">
  import { onMount } from "svelte";
  import WelcomeScreen from "$lib/components/WelcomeScreen.svelte";
  import AppHeader from "$lib/components/AppHeader.svelte";
  import MediaPreviewModal from "./MediaPreviewModal.svelte";
  import ProjectsTab from "./ProjectsTab.svelte";
  import MediaTab from "./MediaTab.svelte";
  import ProjectDetailsTab from "./ProjectDetailsTab.svelte";
  import CreateProjectModal from "./CreateProjectModal.svelte";
  import MaterialsModal from "./MaterialsModal.svelte";
  import AuthModal from "./AuthModal.svelte";

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
  let error = $state("");
  let success = $state("");

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
  let newProjectName = $state("");
  let newProjectTitle = $state("");

  // Media management
  let activeTab = $state("projects");
  let selectedFile = $state<File | null>(null);
  let uploadLevel = $state("public"); // 'public', 'user', 'project'
  let isUploading = $state(false);
  let mediaTabRef = $state<any>(null);

  // Materials management
  let showMaterialsModal = $state(false);
  let materialsTab = $state("public"); // 'public', 'user', 'project'
  let materialsCloseCallback = $state<(() => void) | undefined>(undefined);
  let previewMedia = $state<{
    type: "image" | "video";
    url: string;
    name: string;
    poster?: string;
  } | null>(null);

  // Video generation
  let generatingVideo = $state(false);
  let generationLogs = $state("");
  let showLogs = $state(false);

  onMount(async () => {
    await checkCurrentUser();
    await loadUserProjects();
  });

  async function checkCurrentUser() {
    try {
      const response = await fetch("/api/auth/user");
      if (response.ok) {
        user = await response.json();
        if (user) console.log("✅ User authenticated:", user.username);
        else console.log("ℹ️ No active session");
      } else if (response.status === 401) {
        user = null;
        console.log("ℹ️ No active session");
      }
    } catch (err) {
      user = null;
      console.error("Failed to check current user:", err);
    } finally {
      checkingAuth = false;
    }
  }

  async function loadUserProjects() {
    if (!user) return;

    try {
      console.log("🔄 Loading user projects...");
      const response = await fetch("/api/projects");
      if (response.ok) {
        projects = await response.json();
        console.log("✅ Projects loaded:", projects);
      } else {
        console.error(
          "❌ Failed to load projects:",
          response.status,
          await response.text(),
        );
        if (response.status === 401) {
          console.log("🔐 Session expired, logging out...");
          user = null;
          projects = [];
          error = "Session expired. Please login again.";
          setTimeout(() => (error = ""), 5000);
        }
      }
    } catch (err) {
      console.error("❌ Error loading projects:", err);
    }
  }

  async function handleLogin(event: Event) {
    event.preventDefault();
    const form = event.target as HTMLFormElement;
    const formData = new FormData(form);

    try {
      const response = await fetch("/api/auth", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (response.ok && data.success) {
        await checkCurrentUser();
        await loadUserProjects();
        showAuth = false;

        if (data.action === "register") {
          success =
            "Registration successful! Welcome to the video content service.";
        } else {
          success = "Login successful!";
        }
        setTimeout(() => (success = ""), 3000);
      } else {
        if (data.action === "login_failed") {
          error = "Invalid username or password.";
        } else {
          error = data.message || "Authentication failed";
        }
        setTimeout(() => (error = ""), 3000);
      }
    } catch (err: unknown) {
      error = "Network error. Please try again.";
      setTimeout(() => (error = ""), 3000);
      console.log(err);
    }
  }

  async function handleLogout() {
    try {
      const response = await fetch("/api/auth/logout", { method: "POST" });

      if (response.ok) {
        await checkCurrentUser();
        projects = [];
        selectedProject = null;
        success = "Logged out successfully!";
        setTimeout(() => (success = ""), 3000);
      } else {
        const errorData = await response.json();
        error = errorData.message || "Logout failed";
        setTimeout(() => (error = ""), 3000);
      }
    } catch (err: unknown) {
      error = "Network error during logout";
      console.log(err);
      setTimeout(() => (error = ""), 3000);
    }
  }

  async function createProject() {
    if (!user || !newProjectName.trim()) return;

    try {
      const response = await fetch("/api/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: newProjectName.trim(),
          title: newProjectTitle.trim() || newProjectName.trim(),
        }),
      });

      if (response.ok) {
        await loadUserProjects();
        showCreateProject = false;
        newProjectName = "";
        newProjectTitle = "";
        success = "Project created successfully!";
        setTimeout(() => (success = ""), 3000);
      } else {
        const errorData = await response.json();
        error = errorData.message || "Failed to create project";
        setTimeout(() => (error = ""), 3000);
      }
    } catch (err) {
      error = "Network error";
      console.log(err);
      setTimeout(() => (error = ""), 3000);
    }
  }

  async function copyProject(project: Project) {
    try {
      const response = await fetch(`/api/projects/${project.id}/copy`, {
        method: "POST",
      });

      if (response.ok) {
        await loadUserProjects();
        const newProject = await response.json();
        selectedProject = newProject;
        activeTab = "project-details";
        success = "Project copied successfully!";
        setTimeout(() => (success = ""), 3000);
      } else {
        error = "Failed to copy project";
        setTimeout(() => (error = ""), 3000);
      }
    } catch (err) {
      error = "Network error";
      console.log(err);
      setTimeout(() => (error = ""), 3000);
    }
  }

  async function deleteProject(projectId: string) {
    try {
      const response = await fetch(`/api/projects/${projectId}`, {
        method: "DELETE",
      });

      if (response.ok) {
        await loadUserProjects();
        if (selectedProject?.id === projectId) {
          selectedProject = null;
        }
        success = "Project deleted successfully!";
        setTimeout(() => (success = ""), 3000);
      } else {
        error = "Failed to delete project";
        setTimeout(() => (error = ""), 3000);
      }
    } catch (err) {
      error = "Network error";
      console.log(err);
      setTimeout(() => (error = ""), 3000);
    }
  }

  function selectProject(project: Project) {
    selectedProject = project;
    activeTab = "project-details";
  }

  async function generateVideo() {
    if (!selectedProject) return;

    generatingVideo = true;
    generationLogs = "";
    showLogs = true;

    try {
      const response = await fetch(
        `/api/projects/${selectedProject.id}/generate`,
        {
          method: "POST",
        },
      );

      if (response.ok) {
        await response.json();
        // Handle video generation response
        success = "Video generation started!";
        setTimeout(() => (success = ""), 3000);
      } else {
        const errorData = await response.json();
        error = errorData.message || "Video generation failed";
        setTimeout(() => (error = ""), 3000);
      }
    } catch (err) {
      error = "Network error during video generation";
      console.log(err);
      setTimeout(() => (error = ""), 3000);
    } finally {
      generatingVideo = false;
    }
  }

  async function uploadMedia() {
    if (!selectedFile) return;

    isUploading = true;
    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("level", uploadLevel);
      console.log("=-======", uploadLevel);

      const response = await fetch("/api/media/upload", {
        method: "POST",
        body: formData,
      });

      if (response.ok) {
        // Dispatch a custom event to notify MediaTab of successful upload
        window.dispatchEvent(new CustomEvent("mediaUploadComplete", {
          detail: { level: uploadLevel }
        }));
        
        await loadUserProjects(); // Refresh if needed
        success = "Media uploaded successfully!";
        setTimeout(() => (success = ""), 3000);
        selectedFile = null;
      } else {
        const errorData = await response.json();
        error = errorData.message || "Upload failed";
        setTimeout(() => (error = ""), 3000);
      }
    } catch (err) {
      error = "Network error during upload";
      console.log(err);
      setTimeout(() => (error = ""), 3000);
    } finally {
      isUploading = false;
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
      class="mb-4 rounded-lg border border-green-400 bg-green-100 p-4 text-green-700"
    >
      {success}
    </div>
  {/if}
  {#if error}
    <div
      class="mb-4 rounded-lg border border-red-400 bg-red-100 p-4 text-red-700"
    >
      {error}
    </div>
  {/if}

  <!-- Main Content -->
  <MediaPreviewModal {previewMedia} onClose={() => (previewMedia = null)} />

  {#if user}
    <!-- Main Tabs -->
    <div class="mb-6">
      <div class="flex rounded-lg bg-gray-100/50 p-1">
        <button
          class="flex-1 rounded-md px-4 py-2 transition-all duration-200"
          class:bg-white={activeTab === "projects"}
          class:text-gray-900={activeTab === "projects"}
          class:text-gray-600={activeTab !== "projects"}
          onclick={() => (activeTab = "projects")}
        >
          Projects
        </button>
        <button
          class="flex-1 rounded-md px-4 py-2 transition-all duration-200"
          class:bg-white={activeTab === "media"}
          class:text-gray-900={activeTab === "media"}
          class:text-gray-600={activeTab !== "media"}
          onclick={() => (activeTab = "media")}
        >
          Media Library
        </button>
        {#if selectedProject}
          <button
            class="flex-1 rounded-md px-4 py-2 transition-all duration-200"
            class:bg-white={activeTab === "project-details"}
            class:text-gray-900={activeTab === "project-details"}
            class:text-gray-600={activeTab !== "project-details"}
            onclick={() => (activeTab = "project-details")}
          >
            Project Details
          </button>
        {/if}
      </div>
    </div>

    {#if activeTab === "projects"}
      <ProjectsTab
        {projects}
        onSelectProject={selectProject}
        onCopyProject={copyProject}
        onDeleteProject={deleteProject}
        onCreateProject={() => (showCreateProject = true)}
      />
    {:else if activeTab === "media"}
      <MediaTab
        bind:this={mediaTabRef}
        {selectedFile}
        bind:uploadLevel
        {selectedProject}
        {isUploading}
        onMediaSelect={(file: File) => (selectedFile = file)}
        onUpload={uploadMedia}
        onPreviewMedia={(media: { type: "image" | "video"; url: string; name: string; poster?: string }) => (previewMedia = media)}
        onMediaSelectionChange={() => {}}
        onMediaSelectionDone={() => {}}
      />
      level: {uploadLevel}
    {:else if activeTab === "project-details" && selectedProject}
      <ProjectDetailsTab
        {selectedProject}
        {generatingVideo}
        {showLogs}
        {generationLogs}
        onGenerateVideo={generateVideo}
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
      newProjectName = "";
      newProjectTitle = "";
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
