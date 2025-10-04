<script lang="ts">
  interface Project {
    id: string;
    name: string;
    title: string;
    createdAt: string;
    updatedAt: string;
    prompt?: string;
    staticSubtitle?: string;
  }

  interface Material {
    id: string;
    projectId: string;
    relativePath: string;
    fileName: string;
    fileType: string;
    createdAt: string;
  }

  interface Props {
    selectedProject: Project;
    generatingVideo: boolean;
    showLogs: boolean;
    generationLogs: string;
    onShowConfigModal: () => void;
    onGenerateVideo: () => void;
    onShowMaterialsModal: (onCloseCallback?: () => void) => void;
    onUpdateProject: (project: Project) => void;
    onPreviewMedia: (media: {
      type: "image" | "video";
      url: string;
      name: string;
      poster?: string;
    }) => void;
  }

  let {
    selectedProject,
    generatingVideo,
    showLogs,
    generationLogs,
    onShowConfigModal,
    onGenerateVideo,
    onShowMaterialsModal,
    onUpdateProject,
    onPreviewMedia,
  }: Props = $props();

  let projectMaterials = $state<Material[]>([]);
  let loadingMaterials = $state(false);

  async function loadProjectMaterials() {
    if (!selectedProject) return;

    loadingMaterials = true;
    try {
      const response = await fetch(
        `/api/projects/${selectedProject.id}/materials`,
      );
      if (response.ok) {
        projectMaterials = await response.json();
      } else {
        console.error("Failed to load project materials");
        projectMaterials = [];
      }
    } catch (err) {
      console.error("Error loading project materials:", err);
      projectMaterials = [];
    } finally {
      loadingMaterials = false;
    }
  }

  function getMediaIcon(type: string): string {
    switch (type) {
      case "image":
        return "🖼️";
      case "video":
        return "🎥";
      case "audio":
        return "🎵";
      default:
        return "📄";
    }
  }

  $effect(() => {
    if (selectedProject) {
      loadProjectMaterials();
      staticSubtitleContent = selectedProject.staticSubtitle || "";
      promptContent = selectedProject.prompt || "hello";
    }
  });

  let isEditingTitle = $state(false);
  let editedTitle = $state("");
  let staticSubtitleContent = $state(selectedProject.staticSubtitle || "");
  let promptContent = $state(selectedProject.prompt || "hello");

  function startEditingTitle() {
    editedTitle = selectedProject.title;
    isEditingTitle = true;
  }

  async function saveTitle() {
    try {
      const response = await fetch(`/api/projects/${selectedProject.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: editedTitle,
          name: selectedProject.name,
        }),
        credentials: "include",
      });
      if (response.ok) {
        onUpdateProject({ ...selectedProject, title: editedTitle });
        isEditingTitle = false;
      } else {
        const errorData = await response.json();
        alert(errorData.message || "Failed to update title");
      }
    } catch (err) {
      alert("Network error");
      console.error(err);
    }
  }

  function cancelTitle() {
    isEditingTitle = false;
  }

  async function loadContent() {
    try {
      const response = await fetch(`/api/projects/${selectedProject.id}`, {
        credentials: "include",
      });
      if (response.ok) {
        const project = await response.json();
        promptContent = project.prompt || "";
        staticSubtitleContent = project.staticSubtitle || "";
        onUpdateProject(project);
      } else {
        alert("Failed to load content");
      }
    } catch (err) {
      alert("Network error");
      console.error(err);
    }
  }

  async function saveContent() {
    try {
      const response = await fetch(`/api/projects/${selectedProject.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: selectedProject.title,
          name: selectedProject.name,
          prompt: promptContent,
          staticSubtitle: staticSubtitleContent,
        }),
        credentials: "include",
      });
      if (response.ok) {
        onUpdateProject({
          ...selectedProject,
          prompt: promptContent,
          staticSubtitle: staticSubtitleContent,
        });
        console.log(selectedProject);
      } else {
        const errorData = await response.json();
        alert(errorData.message || "Failed to save content");
      }
    } catch (err) {
      alert("Network error");
      console.error(err);
    }
  }

  async function removeMaterial(materialId: string) {
    try {
      const response = await fetch(`/api/projects/${selectedProject.id}/materials?materialId=${materialId}`, {
        method: 'DELETE',
        credentials: 'include',
      });
      if (response.ok) {
        loadProjectMaterials();
      } else {
        const errorData = await response.json();
        alert(errorData.message || 'Failed to remove material');
      }
    } catch (err) {
      alert('Network error');
      console.error(err);
    }
  }
</script>

<!-- Project Details Tab -->
<div class="space-y-6">
  <!-- Project Header -->
  <div
    class="rounded-2xl border border-white/20 bg-white/60 p-6 shadow-lg backdrop-blur-sm"
  >
    <div class="flex items-center justify-between">
      <div>
        {#if isEditingTitle}
          <div class="flex items-center gap-2 mb-1">
            <input
              bind:value={editedTitle}
              class="text-xl font-semibold border rounded px-2 py-1"
            />
            <button
              onclick={saveTitle}
              class="text-green-600 hover:text-green-800">Save</button
            >
            <button
              onclick={cancelTitle}
              class="text-red-600 hover:text-red-800">Cancel</button
            >
          </div>
        {:else}
          <div class="flex items-center gap-2 mb-1">
            <h2 class="text-xl font-semibold">{selectedProject.title}</h2>
            <button onclick={startEditingTitle} aria-label="Edit title">
              <svg
                class="h-5 w-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                ></path>
              </svg>
            </button>
          </div>
        {/if}
        <div class="flex items-center gap-2">
          <p class="text-gray-600">{selectedProject.name}</p>
        </div>
        <!-- todo: PLACE folder relatedto AIV_VAULT_FOLDER of selectedProject here -->
      </div>
      <div class="flex gap-2">
        <button
          onclick={onShowConfigModal}
          class="rounded-lg bg-gray-500 px-4 py-2 text-white transition-colors hover:bg-gray-600"
        >
          Configuration
        </button>
        <button
          onclick={onGenerateVideo}
          disabled={generatingVideo}
          class="rounded-lg bg-gradient-to-r from-purple-500 to-pink-500 px-6 py-3 text-white transition-all duration-200 hover:from-purple-600 hover:to-pink-600 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {#if generatingVideo}
            <div class="flex items-center space-x-2">
              <div
                class="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"
              ></div>
              <span>Generating...</span>
            </div>
          {:else}
            Generate Video
          {/if}
        </button>
      </div>
    </div>
  </div>

  <!-- Project Content -->
  <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
    <!-- Prompt Editor -->
    <div
      class="rounded-2xl border border-white/20 bg-white/60 p-6 shadow-lg backdrop-blur-sm"
    >
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-lg font-semibold">Prompt Editor</h3>
        <div class="flex gap-2">
          <button
            onclick={loadContent}
            class="px-3 py-1 text-sm bg-gray-500 text-white rounded hover:bg-gray-600 transition-colors"
          >
            Reload Content
          </button>
          <button
            onclick={saveContent}
            class="px-3 py-1 text-sm bg-green-500 text-white rounded hover:bg-green-600 transition-colors"
          >
            Save Changes
          </button>
        </div>
      </div>
      prompt: {promptContent}
      <textarea
        bind:value={promptContent}
        placeholder="Enter your video generation prompt..."
        class="h-48 w-full resize-none rounded-lg border border-gray-300 px-4 py-3 focus:border-transparent focus:ring-2 focus:ring-blue-500"
      ></textarea>
      <p class="mt-2 text-sm text-gray-500">
        This prompt will be used to generate subtitles for your video.
      </p>
    </div>

    <!-- Static Subtitle -->
    <div
      class="rounded-2xl border border-white/20 bg-white/60 p-6 shadow-lg backdrop-blur-sm"
    >
      <h3 class="mb-4 text-lg font-semibold">Static Subtitle</h3>
      <textarea
        bind:value={staticSubtitleContent}
        placeholder="Enter static subtitle text (optional)..."
        class="h-48 w-full resize-none rounded-lg border border-gray-300 px-4 py-3 focus:border-transparent focus:ring-2 focus:ring-blue-500"
      ></textarea>
      <p class="mt-2 text-sm text-gray-500">
        If provided, this will override the generated subtitles.
      </p>
    </div>
  </div>

  <!-- Materials Management -->
  <div
    class="rounded-2xl border border-white/20 bg-white/60 p-6 shadow-lg backdrop-blur-sm"
  >
    <div class="flex items-center justify-between mb-6">
      <h3 class="text-lg font-semibold">Project Materials</h3>
      <button
        class="rounded-lg bg-blue-500 px-4 py-2 text-white transition-colors hover:bg-blue-600"
        onclick={() => onShowMaterialsModal(() => loadProjectMaterials())}
      >
        Manage Materials
      </button>
    </div>

    <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
      {#if loadingMaterials}
        <div class="col-span-full flex items-center justify-center py-8">
          <div class="flex items-center space-x-2">
            <div
              class="h-4 w-4 animate-spin rounded-full border-2 border-blue-500 border-t-transparent"
            ></div>
            <span>Loading materials...</span>
          </div>
        </div>
      {:else if projectMaterials.length === 0}
        <div class="col-span-full text-center py-8 text-gray-500">
          <div class="text-gray-400 mb-2">
            <svg
              class="mx-auto h-12 w-12"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
              ></path>
            </svg>
          </div>
          <p>No materials added to this project yet</p>
          <p class="text-sm mt-1">
            Click "Manage Materials" to add files from your media library
          </p>
        </div>
      {:else}
        {#each projectMaterials as material (material.id)}
          {@const url = `/api/media/file/${material.relativePath.split("/")[0] === "public" ? "public" : "user"}/${material.relativePath.split("/").slice(2).join("/")}`}
          <div
            class="group relative w-full overflow-hidden rounded-lg border-2 border-gray-200 bg-white transition-all hover:shadow-md"
          >
            <button
              onclick={() => removeMaterial(material.id)}
              class="absolute top-2 right-2 z-10 rounded-full bg-red-500 p-1 text-white shadow-md opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-600 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
              aria-label="Remove material"
            >
              <svg
                class="h-4 w-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
            {#if material.fileType === "image"}
              <button
                type="button"
                class="w-full focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                onclick={() => onPreviewMedia({ type: "image", url, name: material.fileName })}
                aria-label={`Preview ${material.fileName}`}
              >
                <div class="aspect-square overflow-hidden bg-gray-100">
                  <img
                    src={url}
                    alt={material.fileName}
                    class="h-full w-full object-cover transition-transform group-hover:scale-105"
                    loading="lazy"
                  />
                </div>
              </button>
            {:else if material.fileType === "video"}
              <button
                type="button"
                class="w-full focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                onclick={() => onPreviewMedia({ type: "video", url, name: material.fileName })}
                aria-label={`Preview ${material.fileName}`}
              >
                <div class="aspect-square overflow-hidden bg-gray-100">
                  <video
                    src={url}
                    class="h-full w-full object-cover"
                    muted
                    preload="metadata"
                    onloadedmetadata={(e) =>
                      ((e.target as HTMLVideoElement).currentTime = 0)}
                  ></video>
                  <div
                    class="absolute inset-0 flex items-center justify-center bg-transparent bg-opacity-20"
                  >
                    <div class="rounded-full bg-white bg-opacity-80 p-2">
                      <svg
                        class="h-6 w-6 text-gray-700"
                        fill="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path d="M8 5v14l11-7z" />
                      </svg>
                    </div>
                  </div>
                </div>
              </button>
            {:else}
              <div
                class="aspect-square flex items-center justify-center bg-gray-100 rounded-lg"
              >
                <span class="text-4xl">{getMediaIcon(material.fileType)}</span>
              </div>
            {/if}

            <div class="p-2">
              <p
                class="truncate text-xs font-medium text-gray-900"
                title={material.fileName}
              >
                {material.fileName}
              </p>
              <p class="text-xs text-gray-500">{material.fileType}</p>
              <p class="text-xs text-gray-400">
                {new Date(material.createdAt).toLocaleDateString()}
              </p>
            </div>
          </div>
        {/each}
      {/if}
    </div>
  </div>

  <!-- Logs -->
  {#if showLogs}
    <div
      class="rounded-2xl border border-white/20 bg-white/60 p-6 shadow-lg backdrop-blur-sm"
    >
      <h3 class="mb-4 text-lg font-semibold">Generation Logs</h3>
      <div class="h-48 overflow-auto rounded-lg bg-gray-900 p-4">
        <pre class="text-sm text-green-400 font-mono">{generationLogs}</pre>
      </div>
    </div>
  {/if}
</div>
