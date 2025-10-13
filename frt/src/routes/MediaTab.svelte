<script lang="ts">
  import { onMount } from 'svelte';

  interface Project {
    id: string;
    title: string;
    video_title: string;
  }

  interface MediaFile {
    name: string;
    type: string;
    size: number;
    modified: string;
    url: string;
  }

  let {
    selectedFile,
    uploadLevel = $bindable('public'),
    selectedProject,
    isUploading,
    onMediaSelect,
    onUpload,
    onPreviewMedia,
    onMediaSelectionChange,
    onMediaSelectionDone
  }: {
    selectedFile: File | null;
    uploadLevel: string;
    selectedProject: Project | null;
    isUploading: boolean;
    onMediaSelect: (file: File) => void;
    onUpload: () => void;
    onPreviewMedia: (media: {
      type: 'image' | 'video';
      url: string;
      name: string;
      poster?: string;
    }) => void;
    onMediaSelectionChange: (selected: MediaFile[]) => void;
    onMediaSelectionDone: (selected: MediaFile[]) => void;
  } = $props();

  // Functions for parent component to call
  function refreshPublicMedia() {
    loadPublicMediaFiles();
  }

  function refreshUserMedia() {
    loadUserMediaFiles();
  }

  function refreshAllMedia() {
    loadPublicMediaFiles();
    loadUserMediaFiles();
  }

  // Expose functions to parent component
  $inspect(() => ({
    refreshPublicMedia,
    refreshUserMedia,
    refreshAllMedia
  }));

  let publicMediaFiles = $state<MediaFile[]>([]);
  let userMediaFiles = $state<MediaFile[]>([]);
  let loadingPublicMedia = $state(false);
  let loadingUserMedia = $state(false);
  let isSelecting = $state(false);
  let selectedMedia = $state<MediaFile[]>([]);
  let isDeleting = $state(false);

  async function loadPublicMediaFiles() {
    loadingPublicMedia = true;
    try {
      console.log('🌐 [CLIENT] Loading public media files...');
      const response = await fetch('/api/media?level=public');
      console.log('🌐 [CLIENT] Public response status:', response.status);
      console.log('🌐 [CLIENT] Public response ok:', response.ok);

      if (response.ok) {
        const data = await response.json();
        console.log('🌐 [CLIENT] Public media data:', data);
        publicMediaFiles = data;
      } else {
        console.error(
          '🌐 [CLIENT] Failed to load public media files:',
          await response.text()
        );
        publicMediaFiles = [];
      }
    } catch (err) {
      console.error('🌐 [CLIENT] Error loading public media files:', err);
      publicMediaFiles = [];
    } finally {
      loadingPublicMedia = false;
    }
  }

  async function loadUserMediaFiles() {
    loadingUserMedia = true;
    try {
      console.log('🌐 [CLIENT] Loading user media files...');
      const response = await fetch('/api/media?level=user');
      console.log('🌐 [CLIENT] Response status:', response.status);
      console.log('🌐 [CLIENT] Response ok:', response.ok);

      if (response.ok) {
        const data = await response.json();
        console.log('🌐 [CLIENT] User media data:', data);
        userMediaFiles = data;
      } else {
        console.error(
          '🌐 [CLIENT] Failed to load user media files:',
          await response.text()
        );
        userMediaFiles = [];
      }
    } catch (err) {
      console.error('🌐 [CLIENT] Error loading user media files:', err);
      userMediaFiles = [];
    } finally {
      loadingUserMedia = false;
    }
  }

  function formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }

  function getMediaIcon(type: string): string {
    switch (type) {
      case 'image':
        return '🖼️';
      case 'video':
        return '🎥';
      case 'audio':
        return '🎵';
      default:
        return '📄';
    }
  }

  function toggleMediaSelection(file: MediaFile) {
    const index = selectedMedia.findIndex(
      (selected) => selected.name === file.name
    );
    if (index > -1) {
      selectedMedia = selectedMedia.filter(
        (selected) => selected.name !== file.name
      );
    } else {
      selectedMedia = [...selectedMedia, file];
    }
    onMediaSelectionChange(selectedMedia);
  }

  async function deleteSelectedMedia() {
    if (selectedMedia.length === 0) return;

    // Filter to only public media files for deletion
    const publicFiles = selectedMedia.filter((file) =>
      publicMediaFiles.some((publicFile) => publicFile.name === file.name)
    );

    if (publicFiles.length === 0) {
      alert('Only public media files can be deleted from this interface.');
      return;
    }

    isDeleting = true;
    try {
      console.log(
        '🗑️ [CLIENT] Deleting media files:',
        publicFiles.map((f) => f.name)
      );
      const response = await fetch('/api/media', {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          level: 'public',
          files: publicFiles.map((f) => f.name)
        })
      });

      if (response.ok) {
        const result = await response.json();
        console.log('🗑️ [CLIENT] Delete result:', result);
        // Reload public media files
        await loadPublicMediaFiles();
        // Clear selection
        selectedMedia = [];
      } else {
        console.error(
          '🗑️ [CLIENT] Failed to delete media:',
          await response.text()
        );
        alert('Failed to delete some media files. Please try again.');
      }
    } catch (err) {
      console.error('🗑️ [CLIENT] Error deleting media:', err);
      alert('An error occurred while deleting media files.');
    } finally {
      isDeleting = false;
    }
  }

  onMount(() => {
    loadPublicMediaFiles();
    loadUserMediaFiles();

    // Listen for media upload completion events
    const handleMediaUploadComplete = (event: CustomEvent) => {
      const { level } = event.detail;
      if (level === 'public') {
        loadPublicMediaFiles();
      } else if (level === 'user') {
        loadUserMediaFiles();
      }
    };

    window.addEventListener(
      'mediaUploadComplete',
      handleMediaUploadComplete as EventListener
    );

    // Cleanup event listener on component destroy
    return () => {
      window.removeEventListener(
        'mediaUploadComplete',
        handleMediaUploadComplete as EventListener
      );
    };
  });
</script>

<!-- Media Library Tab -->
<div
  class="rounded-2xl border border-white/20 bg-white/60 p-6 shadow-lg backdrop-blur-sm"
>
  <h2 class="mb-6 text-xl font-semibold">Media Library</h2>

  <div class="space-y-6">
    <!-- Upload Section -->
    <div
      class="rounded-lg border-2 border-dashed border-gray-300 p-6 text-center transition-colors hover:border-blue-400"
    >
      <input
        type="file"
        accept="image/*,video/*"
        onchange={(e) => {
          const target = e.target as HTMLInputElement;
          const file: File | null = target.files?.[0] || null;
          if (file) onMediaSelect(file);
        }}
        class="hidden"
        id="media-upload"
      />
      <label
        for="media-upload"
        class="flex cursor-pointer flex-col items-center space-y-2"
      >
        <svg
          class="h-12 w-12 text-gray-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
          ></path>
        </svg>
        <span class="text-gray-600">Click to upload media files</span>
        <span class="text-sm text-gray-500">Images and videos supported</span>
      </label>

      {#if selectedFile}
        <div class="mt-4 rounded-lg bg-blue-50 p-3">
          <span class="text-sm text-blue-800">{selectedFile.name}</span>
        </div>
      {/if}
    </div>

    <!-- Upload Options -->
    {#if selectedFile}
      <div class="space-y-4">
        <div>
          <fieldset>
            <legend class="mb-2 block text-sm font-medium text-gray-700"
              >Upload Level</legend
            >
            <div class="flex gap-4">
              <label class="flex items-center">
                <input
                  type="radio"
                  bind:group={uploadLevel}
                  value="public"
                  class="mr-2"
                />
                <span class="text-sm">Public</span>
              </label>
              <label class="flex items-center">
                <input
                  type="radio"
                  bind:group={uploadLevel}
                  value="user"
                  class="mr-2"
                />
                <span class="text-sm">User Level</span>
              </label>
              {#if selectedProject}
                <label class="flex items-center">
                  <input
                    type="radio"
                    bind:group={uploadLevel}
                    value="project"
                    class="mr-2"
                  />
                  <span class="text-sm"
                    >Project Level ({selectedProject.title})</span
                  >
                </label>
              {/if}
            </div>
          </fieldset>
        </div>

        <button
          onclick={onUpload}
          disabled={isUploading}
          class="w-full rounded-lg bg-gradient-to-r from-green-500 to-blue-500 py-3 text-white transition-all duration-200 hover:from-green-600 hover:to-blue-600 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {#if isUploading}
            <div class="flex items-center justify-center space-x-2">
              <div
                class="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"
              ></div>
              <span>Uploading...</span>
            </div>
          {:else}
            Upload Media
          {/if}
        </button>
      </div>
    {/if}

    <!-- Media Browser -->
    <div class="mt-8 space-y-8">
      <!-- Public Media Section -->
      <div>
        <div class="mb-4 flex items-center justify-between">
          <h3 class="text-lg font-medium text-gray-900">Public Media</h3>
          <div class="flex items-center space-x-2">
            {#if selectedMedia.length > 0}
              <button
                onclick={deleteSelectedMedia}
                disabled={isDeleting}
                class="rounded-lg border border-gray-300 px-3 py-1 text-sm text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {#if isDeleting}
                  Deleting...
                {:else}
                  Delete
                {/if}
              </button>
            {/if}
            <button
              onclick={() => {
                isSelecting = !isSelecting;
                if (!isSelecting) {
                  selectedMedia = [];
                  onMediaSelectionChange(selectedMedia);
                } else {
                  onMediaSelectionDone(selectedMedia);
                }
              }}
              class="rounded-lg border border-gray-300 px-3 py-1 text-sm text-gray-700 hover:bg-gray-50"
            >
              {isSelecting ? 'Done' : 'Select'}
            </button>
            <button
              onclick={loadPublicMediaFiles}
              disabled={loadingPublicMedia}
              class="rounded-lg border border-gray-300 px-3 py-1 text-sm text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {#if loadingPublicMedia}
                <div class="flex items-center space-x-1">
                  <div
                    class="h-3 w-3 animate-spin rounded-full border border-gray-400 border-t-transparent"
                  ></div>
                  <span>Loading...</span>
                </div>
              {:else}
                Refresh
              {/if}
            </button>
          </div>
        </div>

        {#if publicMediaFiles.length === 0 && !loadingPublicMedia}
          <div
            class="rounded-lg border-2 border-dashed border-gray-200 p-8 text-center"
          >
            <div class="text-gray-400">
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
              <p class="mt-2 text-sm text-gray-500">
                No public media files found
              </p>
            </div>
          </div>
        {:else}
          <div
            class="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5"
          >
            {#each publicMediaFiles as file (file.name)}
              <button
                class={`group relative w-full overflow-hidden rounded-lg border-2 {selectedMedia.some( (selected) => selected.name === file.name,) ? 'border-blue-500' : 'border-gray-200'} bg-white transition-all hover:shadow-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2`}
                onclick={() => {
                  if (isSelecting) {
                    toggleMediaSelection(file);
                  } else {
                    onPreviewMedia({
                      type: file.type === 'image' ? 'image' : 'video',
                      url: file.url,
                      name: file.name
                    });
                  }
                }}
                aria-label={isSelecting
                  ? `Select ${file.name}`
                  : `Preview ${file.name}`}
              >
                {#if file.type === 'image'}
                  <div class="aspect-square overflow-hidden bg-gray-100">
                    <img
                      src={file.url}
                      alt={file.name}
                      class="h-full w-full object-cover transition-transform group-hover:scale-105"
                      loading="lazy"
                    />
                  </div>
                {:else if file.type === 'video'}
                  <div class="aspect-square overflow-hidden bg-gray-100">
                    <video
                      src={file.url}
                      class="h-full w-full object-cover"
                      muted
                      preload="metadata"
                      onloadedmetadata={(e) =>
                        ((e.target as HTMLVideoElement).currentTime = 0)}
                    ></video>
                    <div
                      class="absolute inset-0 flex items-center justify-center bg-opacity-20"
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
                    class="aspect-square flex items-center justify-center bg-gray-100"
                  >
                    <span class="text-4xl">{getMediaIcon(file.type)}</span>
                  </div>
                {/if}

                {#if selectedMedia.some((selected) => selected.name === file.name)}
                  <div
                    class="absolute top-2 right-2 rounded-full bg-blue-500 p-1"
                  >
                    <svg
                      class="h-4 w-4 text-white"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fill-rule="evenodd"
                        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                        clip-rule="evenodd"
                      />
                    </svg>
                  </div>
                {/if}

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
              </button>
            {/each}
          </div>
        {/if}
      </div>

      <!-- User Media Section -->
      <div>
        <div class="mb-4 flex items-center justify-between">
          <h3 class="text-lg font-medium text-gray-900">Your Media</h3>
          <div class="flex items-center space-x-2">
            <button
              onclick={() => {
                isSelecting = !isSelecting;
                if (!isSelecting) {
                  selectedMedia = [];
                  onMediaSelectionChange(selectedMedia);
                } else {
                  onMediaSelectionDone(selectedMedia);
                }
              }}
              class="rounded-lg border border-gray-300 px-3 py-1 text-sm text-gray-700 hover:bg-gray-50"
            >
              {isSelecting ? 'Done' : 'Select'}
            </button>
            <button
              onclick={loadUserMediaFiles}
              disabled={loadingUserMedia}
              class="rounded-lg border border-gray-300 px-3 py-1 text-sm text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {#if loadingUserMedia}
                <div class="flex items-center space-x-1">
                  <div
                    class="h-3 w-3 animate-spin rounded-full border border-gray-400 border-t-transparent"
                  ></div>
                  <span>Loading...</span>
                </div>
              {:else}
                Refresh
              {/if}
            </button>
          </div>
        </div>

        {#if userMediaFiles.length === 0 && !loadingUserMedia}
          <div
            class="rounded-lg border-2 border-dashed border-gray-200 p-8 text-center"
          >
            <div class="text-gray-400">
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
              <p class="mt-2 text-sm text-gray-500">
                No user media files found
              </p>
            </div>
          </div>
        {:else}
          <div
            class="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5"
          >
            {#each userMediaFiles as file (file.name)}
              <button
                class="group relative w-full overflow-hidden rounded-lg border-2 {selectedMedia.some(
                  (selected) => selected.name === file.name
                )
                  ? 'border-blue-500'
                  : 'border-gray-200'} bg-white transition-all hover:shadow-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                onclick={() => {
                  if (isSelecting) {
                    toggleMediaSelection(file);
                  } else {
                    onPreviewMedia({
                      type: file.type === 'image' ? 'image' : 'video',
                      url: file.url,
                      name: file.name
                    });
                  }
                }}
                aria-label={isSelecting
                  ? `Select ${file.name}`
                  : `Preview ${file.name}`}
              >
                {#if file.type === 'image'}
                  <div class="aspect-square overflow-hidden bg-gray-100">
                    <img
                      src={file.url}
                      alt={file.name}
                      class="h-full w-full object-cover transition-transform group-hover:scale-105"
                      loading="lazy"
                    />
                  </div>
                {:else if file.type === 'video'}
                  <div class="aspect-square overflow-hidden bg-gray-100">
                    <video
                      src={file.url}
                      class="h-full w-full object-cover"
                      muted
                      preload="metadata"
                      onloadedmetadata={(e) =>
                        ((e.target as HTMLVideoElement).currentTime = 0)}
                    ></video>
                    <div
                      class="absolute inset-0 flex items-center justify-center bg-opacity-20"
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
                    class="aspect-square flex items-center justify-center bg-gray-100"
                  >
                    <span class="text-4xl">{getMediaIcon(file.type)}</span>
                  </div>
                {/if}

                {#if selectedMedia.some((selected) => selected.name === file.name)}
                  <div
                    class="absolute top-2 right-2 rounded-full bg-blue-500 p-1"
                  >
                    <svg
                      class="h-4 w-4 text-white"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fill-rule="evenodd"
                        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                        clip-rule="evenodd"
                      />
                    </svg>
                  </div>
                {/if}

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
              </button>
            {/each}
          </div>
        {/if}
      </div>
    </div>
  </div>
</div>
