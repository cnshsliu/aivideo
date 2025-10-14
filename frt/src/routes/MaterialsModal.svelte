<script lang="ts">
  import TreeNode from '$lib/components/TreeNode.svelte';

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
    url: string | null;
  }

  interface TreeNode {
    name: string;
    type: string; // 'folder' or file type like 'image', 'video', etc.
    path: string;
    children?: TreeNode[];
    expanded?: boolean;
    loading?: boolean;
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
      type: 'image' | 'video';
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
    onPreviewMedia
  }: Props = $props();

  let publicTree = $state<TreeNode>({ name: 'Public Media', type: 'folder', path: '', children: [], expanded: true });
  let userTree = $state<TreeNode>({ name: 'User Media', type: 'folder', path: '', children: [], expanded: true });
  let projectMaterials = $state<Material[]>([]);
  let loadingPublic = $state(false);
  let loadingUser = $state(false);
  let hasLoaded = $state(false);
  let showCreateFolder = $state(false);
  let newFolderName = $state('');
  let currentFolderPath = $state('');
  let selectedFolderNode = $state<TreeNode | null>(null);
  let currentFolderContents = $state<MediaFile[]>([]);
  let loadingContents = $state(false);
  let currentIsPublic = $state(true);
  let lastFolderKey = 'materialsModal_lastFolder';

  let addedPublicFiles = $derived.by(
    () =>
      new Set(
        projectMaterials
          .filter((material) =>
            material.relativePath.startsWith('public/media/')
          )
          .map((material) => material.relativePath.replace('public/media/', ''))
      )
  );

  let addedUserFiles = $derived.by(
    () =>
      new Set(
        projectMaterials
          .filter((material) =>
            currentUsername
              ? material.relativePath.startsWith(`${currentUsername}/`)
              : false
          )
          .map((material) => material.relativePath.replace(`${currentUsername}/media/`, ''))
      )
  );

  async function loadPublicMedia(folderPath = '') {
    loadingPublic = true;
    try {
      const response = await fetch(`/api/media?level=public${folderPath ? `&folder=${encodeURIComponent(folderPath)}` : ''}`);
      if (response.ok) {
        const files = await response.json();
        updateTree(publicTree, folderPath, files);
      } else {
        console.error('Failed to load public media');
      }
    } catch (err) {
      console.error('Error loading public media:', err);
    } finally {
      loadingPublic = false;
    }
  }

  async function loadUserMedia(folderPath = '') {
    loadingUser = true;
    try {
      const response = await fetch(`/api/media?level=user${folderPath ? `&folder=${encodeURIComponent(folderPath)}` : ''}`);
      if (response.ok) {
        const files = await response.json();
        updateTree(userTree, folderPath, files);
      } else {
        console.error('Failed to load user media');
      }
    } catch (err) {
      console.error('Error loading user media:', err);
    } finally {
      loadingUser = false;
    }
  }

  function updateTree(tree: TreeNode, folderPath: string, files: MediaFile[]) {
    if (folderPath === '') {
      // Root level - only include folders
      tree.children = files
        .filter((file) => file.type === 'folder')
        .map((file) => ({
          name: file.name,
          type: file.type,
          path: file.name,
          children: [],
          expanded: false
        }));
    } else {
      // Find the folder node and update its children - only include folders
      const pathParts = folderPath.split('/');
      let currentNode = tree;
      for (const part of pathParts) {
        const child = currentNode.children?.find((c) => c.name === part);
        if (child) {
          currentNode = child;
        } else {
          break;
        }
      }
      if (currentNode) {
        currentNode.children = files
          .filter((file) => file.type === 'folder')
          .map((file) => ({
            name: file.name,
            type: file.type,
            path: folderPath + '/' + file.name,
            children: [],
            expanded: false
          }));
        currentNode.loading = false;
      }
    }
  }

  async function loadProjectMaterials() {
    if (!selectedProject) return;

    try {
      const response = await fetch(
        `/api/projects/${selectedProject.id}/materials`
      );
      if (response.ok) {
        projectMaterials = await response.json();
      } else {
        console.error('Failed to load project materials');
        projectMaterials = [];
      }
    } catch (err) {
      console.error('Error loading project materials:', err);
      projectMaterials = [];
    }
  }

  function isMaterialInProject(filePath: string, isPublic: boolean): boolean {
    return isPublic ? addedPublicFiles.has(filePath) : addedUserFiles.has(filePath);
  }

  async function addMaterialToProject(filePath: string, isPublic: boolean) {
    if (!selectedProject || (isPublic === false && !currentUsername)) return;

    try {
      const relativePath = isPublic
        ? `public/media/${filePath}`
        : `${currentUsername}/media/${filePath}`;

      const fileName = filePath.split('/').pop() || '';
      const fileExtension = fileName.split('.').pop()?.toLowerCase();
      const fileType = fileExtension && ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg'].includes(fileExtension) ? 'image' : 'video';

      const response = await fetch(
        `/api/projects/${selectedProject.id}/materials`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            relativePath,
            fileName,
            fileType
          })
        }
      );

      if (response.ok) {
        await loadProjectMaterials(); // Refresh materials
      } else {
        const error = await response.json();
        alert(error.message || 'Failed to add material');
      }
    } catch (err) {
      console.error('Error adding material:', err);
      alert('Network error');
    }
  }

  async function removeMaterialFromProject(materialId: string) {
    if (!selectedProject) return;

    try {
      const response = await fetch(
        `/api/projects/${selectedProject.id}/materials?materialId=${materialId}`,
        {
          method: 'DELETE'
        }
      );

      if (response.ok) {
        await loadProjectMaterials(); // Refresh materials
      } else {
        const error = await response.json();
        alert(error.message || 'Failed to remove material');
      }
    } catch (err) {
      console.error('Error removing material:', err);
      alert('Network error');
    }
  }

  async function loadFolderContent(node: TreeNode, isPublic: boolean) {
    selectedFolderNode = node;
    currentFolderPath = node.path;
    currentIsPublic = isPublic;

    // Save the current folder to localStorage
    saveLastFolder(isPublic, node.path);

    loadingContents = true;
    try {
      const level = isPublic ? 'public' : 'user';
      const folderParam = node.path ? `&folder=${encodeURIComponent(node.path)}` : '';
      const response = await fetch(`/api/media?level=${level}${folderParam}`);

      if (response.ok) {
        const data = await response.json();
        currentFolderContents = data.filter((file: MediaFile) => file.type !== 'folder');
      } else {
        console.error('Failed to load folder content:', await response.text());
        currentFolderContents = [];
      }
    } catch (err) {
      console.error('Error loading folder content:', err);
      currentFolderContents = [];
    } finally {
      loadingContents = false;
    }
  }

  async function toggleFolder(node: TreeNode, isPublic: boolean) {
    // Load folder content into the right panel and toggle expand/collapse
    await loadFolderContent(node, isPublic);

    if (node.expanded) {
      node.expanded = false;
    } else {
      node.expanded = true;
      if (!node.children || node.children.length === 0) {
        node.loading = true;
        if (isPublic) {
          await loadPublicMedia(node.path);
        } else {
          await loadUserMedia(node.path);
        }
      }
    }
  }

  async function loadFolderContentOnly(node: TreeNode, isPublic: boolean) {
    // Load folder content into the right panel without toggling expand
    await loadFolderContent(node, isPublic);
  }

  function formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }

  function saveLastFolder(isPublic: boolean, path: string) {
    try {
      const folderData = {
        isPublic,
        path,
        timestamp: Date.now()
      };
      localStorage.setItem(lastFolderKey, JSON.stringify(folderData));
    } catch (err) {
      console.error('Failed to save last folder to localStorage:', err);
    }
  }

  function getLastFolder() {
    try {
      const stored = localStorage.getItem(lastFolderKey);
      if (stored) {
        const folderData = JSON.parse(stored);
        // Check if data is valid and recent (within 30 days)
        if (folderData && folderData.timestamp &&
            (Date.now() - folderData.timestamp) < 30 * 24 * 60 * 60 * 1000) {
          return folderData;
        }
      }
    } catch (err) {
      console.error('Failed to read last folder from localStorage:', err);
    }
    return null;
  }

  async function restoreLastFolder() {
    const lastFolder = getLastFolder();
    if (!lastFolder) {
      // Default to Public Media root
      await loadFolderContentOnly(publicTree, true);
      return;
    }

    const { isPublic, path } = lastFolder;

    // Try to find and navigate to the saved folder
    try {
      if (isPublic) {
        // Check if the path exists in public media
        const response = await fetch(`/api/media?level=public${path ? `&folder=${encodeURIComponent(path)}` : ''}`);
        if (response.ok) {
          // Find the node in the tree
          const pathParts = path ? path.split('/') : [];
          let currentNode = publicTree;

          for (const part of pathParts) {
            const child = currentNode.children?.find((c) => c.name === part);
            if (child) {
              currentNode = child;
            } else {
              // Path doesn't exist, fall back to root
              await loadFolderContentOnly(publicTree, true);
              return;
            }
          }

          await loadFolderContentOnly(currentNode, true);
          return;
        }
      } else {
        // Check if the path exists in user media
        const response = await fetch(`/api/media?level=user${path ? `&folder=${encodeURIComponent(path)}` : ''}`);
        if (response.ok) {
          // Find the node in the tree
          const pathParts = path ? path.split('/') : [];
          let currentNode = userTree;

          for (const part of pathParts) {
            const child = currentNode.children?.find((c) => c.name === part);
            if (child) {
              currentNode = child;
            } else {
              // Path doesn't exist, fall back to root
              await loadFolderContentOnly(publicTree, true);
              return;
            }
          }

          await loadFolderContentOnly(currentNode, false);
          return;
        }
      }
    } catch (err) {
      console.error('Error restoring last folder:', err);
    }

    // If we get here, the saved folder doesn't exist anymore, default to Public Media
    await loadFolderContentOnly(publicTree, true);
  }

  async function createFolder() {
    if (!newFolderName.trim()) return;

    try {
      const response = await fetch('/api/media', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          level: currentIsPublic ? 'public' : 'user',
          folderName: newFolderName.trim(),
          parentFolder: currentFolderPath
        })
      });

      if (response.ok) {
        // Refresh the current folder
        if (currentIsPublic) {
          await loadPublicMedia(currentFolderPath);
        } else {
          await loadUserMedia(currentFolderPath);
        }
        newFolderName = '';
        showCreateFolder = false;
      } else {
        const error = await response.json();
        alert(error.message || 'Failed to create folder');
      }
    } catch (err) {
      console.error('Error creating folder:', err);
      alert('Network error');
    }
  }

  $effect(() => {
    if (selectedProject) {
      projectMaterials = [];
    }
  });

  $effect(() => {
    if (showMaterialsModal && !hasLoaded) {
      // Load the media trees first
      Promise.all([
        loadPublicMedia(),
        loadUserMedia()
      ]).then(() => {
        // Then try to restore the last folder
        restoreLastFolder();
      });
      if (selectedProject) {
        loadProjectMaterials();
      }
      hasLoaded = true;
    }
  });

  $effect(() => {
    if (!showMaterialsModal) {
      hasLoaded = false;
      publicTree = { name: 'Public Media', type: 'folder', path: '', children: [], expanded: true };
      userTree = { name: 'User Media', type: 'folder', path: '', children: [], expanded: true };
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
      class="w-full h-full rounded-none bg-white p-6 shadow-xl overflow-hidden"
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

      <!-- Tree View -->
      <div class="flex gap-4 h-[calc(100vh-200px)]">
        <!-- Tree Navigation -->
        <div class="w-80 bg-gray-50 rounded-lg p-4 overflow-y-auto">
          {#if loadingPublic}
            <div class="flex items-center justify-center py-4">
              <div class="animate-spin rounded-full border-2 border-blue-500 border-t-transparent w-6 h-6"></div>
              <span class="ml-2">Loading Public...</span>
            </div>
          {:else}
            <TreeNode
              node={publicTree}
              isPublic={true}
              selectedNode={selectedFolderNode}
              onToggle={toggleFolder}
              onLoadContent={loadFolderContentOnly}
              onCreateFolder={(path, isPublic) => {
                currentFolderPath = path;
                currentIsPublic = isPublic;
                showCreateFolder = true;
              }}
              onRefresh={(isPublic) =>
                isPublic ? loadPublicMedia() : loadUserMedia()}
            />
          {/if}
          {#if loadingUser}
            <div class="flex items-center justify-center py-4">
              <div class="animate-spin rounded-full border-2 border-blue-500 border-t-transparent w-6 h-6"></div>
              <span class="ml-2">Loading User...</span>
            </div>
          {:else}
            <TreeNode
              node={userTree}
              isPublic={false}
              selectedNode={selectedFolderNode}
              onToggle={toggleFolder}
              onLoadContent={loadFolderContentOnly}
              onCreateFolder={(path, isPublic) => {
                currentFolderPath = path;
                currentIsPublic = isPublic;
                showCreateFolder = true;
              }}
              onRefresh={(isPublic) =>
                isPublic ? loadPublicMedia() : loadUserMedia()}
            />
          {/if}
        </div>

        <!-- Content Area -->
        <div class="flex-1 bg-white rounded-lg border p-4 overflow-y-auto">
          {#if selectedFolderNode}
            <div class="mb-4">
              <h3 class="text-lg font-semibold">{selectedFolderNode.name}</h3>
              <p class="text-sm text-gray-500">
                {currentFolderContents.length} items
              </p>
            </div>

            {#if currentFolderContents.length > 0}
              <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
                {#each currentFolderContents as file}
                  <div class="group relative border rounded-lg p-2 hover:bg-gray-50 cursor-pointer transition-colors {isMaterialInProject(`${selectedFolderNode!.path}/${file.name}`, currentIsPublic) ? 'border-green-500 bg-green-50' : 'border-gray-200'}">
                    <div class="aspect-square flex items-center justify-center bg-gray-100 rounded mb-2 group">
                      {#if file.type === 'image' && file.url}
                        <div class="relative w-full h-full">
                          <img
                            src={file.url}
                            alt={file.name}
                            class="w-full h-full object-cover rounded"
                          />
                          <div class="absolute inset-0 flex items-center justify-center bg-black/20 rounded opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          class="bg-green-500 text-white rounded-full p-1 hover:bg-green-600 text-xs"
                          onclick={() => addMaterialToProject(`${selectedFolderNode!.path}/${file.name}`, currentIsPublic)}
                          title="Add to project"
                          aria-label="Add to project"
                        >
                          <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24">
                            <circle cx="12" cy="12" r="10" fill="rgb(59 130 246)" />
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" stroke="white" d="M12 4v16m8-8H4"></path>
                          </svg>
                        </button>
                          </div>
                        </div>
                      {:else if file.type === 'video'}
                        {#if file.url}
                          <div class="relative w-full h-full">
                            <video
                              src={file.url!}
                              class="w-full h-full object-cover rounded"
                              preload="metadata"
                              muted
                              playsinline
                            ></video>
                            <div class="absolute inset-0 flex items-center justify-center bg-black/20 rounded opacity-0 group-hover:opacity-100 transition-opacity">
                              <button
                                class="bg-white/90 text-black rounded-full w-8 h-8 flex items-center justify-center hover:bg-white"
                                onclick={() => onPreviewMedia({
                                  type: 'video',
                                  url: file.url!,
                                  name: file.name
                                })}
                              >
                                ▶️
                              </button>
                            </div>
                          </div>
                        {:else}
                          <div class="flex flex-col items-center">
                            <span class="text-2xl">🎥</span>
                          </div>
                        {/if}
                      {:else}
                        <span class="text-2xl">
                          {#if file.type === 'image'}
                            🖼️
                          {:else if file.type === 'video'}
                            🎥
                          {:else if file.type === 'audio'}
                            🎵
                          {:else}
                            📄
                          {/if}
                        </span>
                      {/if}
                    </div>
                    <div class="text-xs truncate" title={file.name}>
                      {file.name}
                    </div>
                    <div class="text-xs text-gray-500">
                      {formatFileSize(file.size)}
                    </div>
                    <div class="mt-2 flex justify-center">
                      {#if isMaterialInProject(`${selectedFolderNode!.path}/${file.name}`, currentIsPublic)}
                        <button
                          class="bg-red-500 text-white rounded-full p-1 hover:bg-red-600 text-xs"
                          onclick={() => {
                            const material = projectMaterials.find(m =>
                              currentIsPublic
                                ? m.relativePath === `public/media/${selectedFolderNode!.path}/${file.name}`
                                : m.relativePath === `${currentUsername}/media/${selectedFolderNode!.path}/${file.name}`
                            );
                            if (material) removeMaterialFromProject(material.id);
                          }}
                          title="Remove from project"
                          aria-label="Remove from project"
                        >
                          <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" stroke="white" d="M6 18L18 6M6 6l12 12"></path>
                          </svg>
                        </button>
                      {:else}
                        <button
                          class="bg-green-500 text-white rounded-full p-1 hover:bg-green-600 text-xs"
                          onclick={() => addMaterialToProject(`${selectedFolderNode!.path}/${file.name}`, currentIsPublic)}
                          title="Add to project"
                          aria-label="Add to project"
                        >
                          <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24">
                            <circle cx="12" cy="12" r="10" fill="rgb(59 130 246)" />
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" stroke="white" d="M12 4v16m8-8H4"></path>
                          </svg>
                        </button>
                      {/if}
                    </div>
                  </div>
                {/each}
              </div>
            {:else}
              <div class="text-center text-gray-500 py-8">
                This folder is empty
              </div>
            {/if}
          {:else}
            <div class="text-center text-gray-500 py-8">
              Select a folder from the tree to view contents
            </div>
          {/if}
        </div>
      </div>

      <!-- Create Folder Modal -->
      {#if showCreateFolder}
        <div class="fixed inset-0 z-60 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div class="bg-white rounded-lg p-6 w-96">
            <h3 class="text-lg font-semibold mb-4">Create New Folder</h3>
            <input
              type="text"
              bind:value={newFolderName}
              placeholder="Folder name"
              class="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              onkeydown={(e) => {
                if (e.key === 'Enter') createFolder();
                if (e.key === 'Escape') showCreateFolder = false;
              }}
            />
            <div class="flex gap-2 mt-4">
              <button
                onclick={createFolder}
                class="flex-1 bg-blue-500 text-white py-2 rounded-lg hover:bg-blue-600"
              >
                Create
              </button>
              <button
                onclick={() => { showCreateFolder = false; newFolderName = ''; }}
                class="flex-1 bg-gray-300 text-gray-700 py-2 rounded-lg hover:bg-gray-400"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      {/if}
    </div>
  </div>
{/if}
