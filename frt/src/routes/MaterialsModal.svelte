<script lang="ts">
  interface Project {
    id: string;
    title: string;
  }

  interface MediaFile {
    name: string;
    type: string;
    size: number;
    modified: string;
    url: string;
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
    showMaterialsModal: boolean;
    materialsTab: string;
    selectedProject: Project | null;
    currentUsername: string | undefined;
    onClose: () => void;
    onPreviewMedia: (media: {
      type: "image" | "video";
      url: string;
      name: string;
      poster?: string;
    }) => void;
  }

  let {
    showMaterialsModal,
    materialsTab,
    selectedProject,
    currentUsername,
    onClose,
    onPreviewMedia,
  }: Props = $props();

  let publicMediaFiles = $state<MediaFile[]>([]);
  let userMediaFiles = $state<MediaFile[]>([]);
  let projectMaterials = $state<Material[]>([]);
  let loadingPublic = $state(false);
  let loadingUser = $state(false);
  let loadingProject = $state(false);
  let hasLoaded = $state(false);

  let addedPublicFiles = $derived.by(
    () =>
      new Set(
        projectMaterials
          .filter((material) =>
            material.relativePath.startsWith("public/media/"),
          )
          .map((material) => material.fileName),
      ),
  );

  let addedUserFiles = $derived.by(
    () =>
      new Set(
        projectMaterials
          .filter((material) =>
            currentUsername
              ? material.relativePath.startsWith(`${currentUsername}/`)
              : false,
          )
          .map((material) => material.fileName),
      ),
  );

  async function loadPublicMedia() {
    loadingPublic = true;
    try {
      const response = await fetch("/api/media?level=public");
      if (response.ok) {
        publicMediaFiles = await response.json();
      } else {
        console.error("Failed to load public media");
        publicMediaFiles = [];
      }
    } catch (err) {
      console.error("Error loading public media:", err);
      publicMediaFiles = [];
    } finally {
      loadingPublic = false;
    }
  }

  async function loadUserMedia() {
    loadingUser = true;
    try {
      const response = await fetch("/api/media?level=user");
      if (response.ok) {
        userMediaFiles = await response.json();
      } else {
        console.error("Failed to load user media");
        userMediaFiles = [];
      }
    } catch (err) {
      console.error("Error loading user media:", err);
      userMediaFiles = [];
    } finally {
      loadingUser = false;
    }
  }

  async function loadProjectMaterials() {
    if (!selectedProject) return;

    loadingProject = true;
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
      loadingProject = false;
    }
  }

  function isMaterialInProject(mediaFile: MediaFile): boolean {
    return addedPublicFiles.has(mediaFile.name);
  }

  function isUserMaterialInProject(mediaFile: MediaFile): boolean {
    return addedUserFiles.has(mediaFile.name);
  }

  async function addMaterialToProject(mediaFile: MediaFile, isPublic: boolean) {
    if (!selectedProject || (isPublic === false && !currentUsername)) return;

    try {
      const relativePath = isPublic
        ? `public/media/${mediaFile.name}`
        : `${currentUsername}/media/${mediaFile.name}`;

      const response = await fetch(
        `/api/projects/${selectedProject.id}/materials`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            relativePath,
            fileName: mediaFile.name,
            fileType: mediaFile.type,
          }),
        },
      );

      if (response.ok) {
        await loadProjectMaterials(); // Refresh materials
      } else {
        const error = await response.json();
        alert(error.message || "Failed to add material");
      }
    } catch (err) {
      console.error("Error adding material:", err);
      alert("Network error");
    }
  }

  async function removeMaterialFromProject(materialId: string) {
    if (!selectedProject) return;

    try {
      const response = await fetch(
        `/api/projects/${selectedProject.id}/materials?materialId=${materialId}`,
        {
          method: "DELETE",
        },
      );

      if (response.ok) {
        await loadProjectMaterials(); // Refresh materials
      } else {
        const error = await response.json();
        alert(error.message || "Failed to remove material");
      }
    } catch (err) {
      console.error("Error removing material:", err);
      alert("Network error");
    }
  }

  function formatFileSize(bytes: number): string {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
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
      projectMaterials = [];
    }
  });

  $effect(() => {
    if (showMaterialsModal && !hasLoaded) {
      loadPublicMedia();
      loadUserMedia();
      if (selectedProject) {
        loadProjectMaterials();
      }
      hasLoaded = true;
    }
  });

  $effect(() => {
    if (!showMaterialsModal) {
      hasLoaded = false;
    }
  });
</script>

<div class="materials-modal">
  <!-- Modal content will be implemented here -->
</div>

{#if showMaterialsModal}
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
  >
    <div
      class="w-full max-w-4xl max-h-[90vh] rounded-2xl bg-white p-6 shadow-xl overflow-hidden"
    >
      <div class="flex items-center justify-between mb-6">
        <h2 class="text-xl font-semibold">Manage Project Materials</h2>
        <button
          onclick={onClose}
          class="text-gray-400 hover:text-gray-600 transition-colors"
          aria-label="Close modal"
        >
          <svg
            class="h-6 w-6"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M6 18L18 6M6 6l12 12"
            ></path>
          </svg>
        </button>
      </div>

      <!-- Materials Tabs -->
      <div class="mb-6">
        <div class="flex rounded-lg bg-gray-100/50 p-1">
          <button
            class="flex-1 rounded-md px-4 py-2 transition-all duration-200"
            class:bg-white={materialsTab === "public"}
            class:text-gray-900={materialsTab === "public"}
            class:text-gray-600={materialsTab !== "public"}
            onclick={() => (materialsTab = "public")}
          >
            Public Media
          </button>
          <button
            class="flex-1 rounded-md px-4 py-2 transition-all duration-200"
            class:bg-white={materialsTab === "user"}
            class:text-gray-900={materialsTab === "user"}
            class:text-gray-600={materialsTab !== "user"}
            onclick={() => (materialsTab = "user")}
          >
            User Media
          </button>
          {#if selectedProject}
            <button
              class="flex-1 rounded-md px-4 py-2 transition-all duration-200"
              class:bg-white={materialsTab === "project"}
              class:text-gray-900={materialsTab === "project"}
              class:text-gray-600={materialsTab !== "project"}
              onclick={() => (materialsTab = "project")}
            >
              Project Media
            </button>
          {/if}
        </div>
      </div>

      <!-- Materials Grid -->
      <div
        class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 max-h-96 overflow-y-auto"
      >
        {#if materialsTab === "public"}
          {#if loadingPublic}
            <div class="col-span-full flex items-center justify-center py-8">
              <div class="flex items-center space-x-2">
                <div
                  class="h-4 w-4 animate-spin rounded-full border-2 border-blue-500 border-t-transparent"
                ></div>
                <span>Loading public media...</span>
              </div>
            </div>
          {:else if publicMediaFiles.length === 0}
            <div class="col-span-full text-center py-8 text-gray-500">
              No public media files found
            </div>
          {:else}
            {#each publicMediaFiles as file (file.name)}
              <div
                class="aspect-square rounded-lg border {isMaterialInProject(
                  file,
                )
                  ? 'border-green-500 bg-green-50'
                  : 'border-gray-200'} bg-white transition-all hover:shadow-md relative group"
              >
                {#if file.type === "image"}
                  <div
                    class="aspect-square overflow-hidden bg-gray-100 rounded-lg"
                  >
                    <img
                      src={file.url}
                      alt={file.name}
                      class="h-full w-full object-cover transition-transform group-hover:scale-105"
                      loading="lazy"
                    />
                  </div>
                {:else if file.type === "video"}
                  <div
                    class="aspect-square overflow-hidden bg-gray-100 rounded-lg relative"
                  >
                    <video
                      src={file.url}
                      class="h-full w-full object-cover"
                      muted
                      preload="metadata"
                      onloadedmetadata={(e) =>
                        ((e.target as HTMLVideoElement).currentTime = 0)}
                    ></video>
                    <div
                      class="absolute inset-0 flex items-center justify-center bg-black bg-opacity-20"
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
                {:else}
                  <div
                    class="aspect-square flex items-center justify-center bg-gray-100 rounded-lg"
                  >
                    <span class="text-4xl">{getMediaIcon(file.type)}</span>
                  </div>
                {/if}

                <!-- Action buttons -->
                <div class="absolute top-2 right-2 flex gap-1">
                  {#if isMaterialInProject(file)}
                    <button
                      class="bg-red-500 text-white rounded-full p-1 opacity-0 group-hover:opacity-100 transition-opacity"
                      onclick={() => {
                        const material = projectMaterials.find(
                          (m) => m.relativePath === `public/media/${file.name}`,
                        );
                        if (material) removeMaterialFromProject(material.id);
                      }}
                      title="Remove from project"
                      aria-label="Remove from project"
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
                        ></path>
                      </svg>
                    </button>
                  {:else}
                    <button
                      class="bg-green-500 text-white rounded-full p-1 opacity-0 group-hover:opacity-100 transition-opacity"
                      onclick={() => addMaterialToProject(file, true)}
                      title="Add to project"
                      aria-label="Add to project"
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
                          d="M12 4v16m8-8H4"
                        ></path>
                      </svg>
                    </button>
                  {/if}
                  <button
                    class="bg-white bg-opacity-90 rounded-full p-1 opacity-0 group-hover:opacity-100 transition-opacity"
                    onclick={() =>
                      onPreviewMedia({
                        type: file.type === "image" ? "image" : "video",
                        url: file.url,
                        name: file.name,
                      })}
                    title="Preview"
                    aria-label="Preview"
                  >
                    <svg
                      class="h-4 w-4 text-gray-800"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                      ></path>
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                      ></path>
                    </svg>
                  </button>
                </div>

                <div class="p-2">
                  <p
                    class="truncate text-xs font-medium text-gray-900"
                    title={file.name}
                  >
                    {file.name}
                  </p>
                  <p class="text-xs text-gray-500">
                    {formatFileSize(file.size)}
                  </p>
                </div>
              </div>
            {/each}
          {/if}
        {:else if materialsTab === "user"}
          {#if loadingUser}
            <div class="col-span-full flex items-center justify-center py-8">
              <div class="flex items-center space-x-2">
                <div
                  class="h-4 w-4 animate-spin rounded-full border-2 border-blue-500 border-t-transparent"
                ></div>
                <span>Loading user media...</span>
              </div>
            </div>
          {:else if userMediaFiles.length === 0}
            <div class="col-span-full text-center py-8 text-gray-500">
              No user media files found
            </div>
          {:else}
            {#each userMediaFiles as file (file.name)}
              <div
                class="aspect-square rounded-lg border {isUserMaterialInProject(
                  file,
                )
                  ? 'border-green-500 bg-green-50'
                  : 'border-gray-200'} bg-white transition-all hover:shadow-md relative group"
              >
                {#if file.type === "image"}
                  <div
                    class="aspect-square overflow-hidden bg-gray-100 rounded-lg"
                  >
                    <img
                      src={file.url}
                      alt={file.name}
                      class="h-full w-full object-cover transition-transform group-hover:scale-105"
                      loading="lazy"
                    />
                  </div>
                {:else if file.type === "video"}
                  <div
                    class="aspect-square overflow-hidden bg-gray-100 rounded-lg relative"
                  >
                    <video
                      src={file.url}
                      class="h-full w-full object-cover"
                      muted
                      preload="metadata"
                      onloadedmetadata={(e) =>
                        ((e.target as HTMLVideoElement).currentTime = 0)}
                    ></video>
                  </div>
                {:else}
                  <div
                    class="aspect-square flex items-center justify-center bg-gray-100 rounded-lg"
                  >
                    <span class="text-4xl">{getMediaIcon(file.type)}</span>
                  </div>
                {/if}

                <!-- Action buttons -->
                <div class="absolute top-2 right-2 flex gap-1">
                  {#if isUserMaterialInProject(file)}
                    <button
                      class="bg-red-500 text-white rounded-full p-1 opacity-0 group-hover:opacity-100 transition-opacity"
                      onclick={() => {
                        const material = projectMaterials.find(
                          (m) =>
                            m.relativePath ===
                            `${currentUsername}/media/${file.name}`,
                        );
                        if (material) removeMaterialFromProject(material.id);
                      }}
                      title="Remove from project"
                      aria-label="Remove from project"
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
                        ></path>
                      </svg>
                    </button>
                  {:else}
                    <button
                      class="bg-green-500 text-white rounded-full p-1 opacity-0 group-hover:opacity-100 transition-opacity"
                      onclick={() => addMaterialToProject(file, false)}
                      title="Add to project"
                      aria-label="Add to project"
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
                          d="M12 4v16m8-8H4"
                        ></path>
                      </svg>
                    </button>
                  {/if}
                  <button
                    class="bg-white bg-opacity-90 rounded-full p-1 opacity-0 group-hover:opacity-100 transition-opacity"
                    onclick={() =>
                      onPreviewMedia({
                        type: file.type === "image" ? "image" : "video",
                        url: file.url,
                        name: file.name,
                      })}
                    title="Preview"
                    aria-label="Preview"
                  >
                    <svg
                      class="h-4 w-4 text-gray-800"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                      ></path>
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                      ></path>
                    </svg>
                  </button>
                </div>

                <div class="p-2">
                  <p
                    class="truncate text-xs font-medium text-gray-900"
                    title={file.name}
                  >
                    {file.name}
                  </p>
                  <p class="text-xs text-gray-500">
                    {formatFileSize(file.size)}
                  </p>
                </div>
              </div>
            {/each}
          {/if}
        {:else if materialsTab === "project"}
          {#if loadingProject}
            <div class="col-span-full flex items-center justify-center py-8">
              <div class="flex items-center space-x-2">
                <div
                  class="h-4 w-4 animate-spin rounded-full border-2 border-blue-500 border-t-transparent"
                ></div>
                <span>Loading project materials...</span>
              </div>
            </div>
          {:else if projectMaterials.length === 0}
            <div class="col-span-full text-center py-8 text-gray-500">
              No materials added to this project yet
            </div>
          {:else}
            {#each projectMaterials as material (material.id)}
              <div
                class="aspect-square rounded-lg border border-blue-200 bg-blue-50 transition-all hover:shadow-md relative group"
              >
                <div
                  class="aspect-square flex items-center justify-center bg-gray-100 rounded-lg"
                >
                  <span class="text-4xl">{getMediaIcon(material.fileType)}</span
                  >
                </div>

                <!-- Remove button -->
                <div class="absolute top-2 right-2">
                  <button
                    class="bg-red-500 text-white rounded-full p-1 opacity-0 group-hover:opacity-100 transition-opacity"
                    onclick={() => removeMaterialFromProject(material.id)}
                    title="Remove from project"
                    aria-label="Remove from project"
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
                      ></path>
                    </svg>
                  </button>
                </div>

                <div class="p-2">
                  <p
                    class="truncate text-xs font-medium text-gray-900"
                    title={material.fileName}
                  >
                    {material.fileName}
                  </p>
                  <p class="text-xs text-gray-500">{material.fileType}</p>
                </div>
              </div>
            {/each}
          {/if}
        {/if}
      </div>

      <!-- Modal Actions -->
      <div class="mt-6 flex gap-3 justify-end">
        <button
          onclick={onClose}
          class="rounded-lg bg-gray-300 px-4 py-2 text-gray-700 transition-colors hover:bg-gray-400"
        >
          Cancel
        </button>
        <button
          class="rounded-lg bg-blue-500 px-4 py-2 text-white transition-colors hover:bg-blue-600"
        >
          Save Materials
        </button>
      </div>
    </div>
  </div>
{/if}
