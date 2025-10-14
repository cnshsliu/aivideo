<script lang="ts">
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
  let selectedFolderPath = $state('');
  let currentFolderContents = $state<MediaFile[]>([]);
  let loadingContents = $state(false);

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
      // Root level
      tree.children = files.map(file => ({
        name: file.name,
        type: file.type as 'folder' | 'file',
        path: file.name,
        children: file.type === 'folder' ? [] : undefined,
        expanded: false
      }));
    } else {
      // Find the folder node and update its children
      const pathParts = folderPath.split('/');
      let currentNode = tree;
      for (const part of pathParts) {
        const child = currentNode.children?.find(c => c.name === part);
        if (child) {
          currentNode = child;
        } else {
          break;
        }
      }
      if (currentNode) {
        currentNode.children = files.map(file => ({
          name: file.name,
          type: file.type as 'folder' | 'file',
          path: folderPath + '/' + file.name,
          children: file.type === 'folder' ? [] : undefined,
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
    const fileName = filePath.split('/').pop() || '';
    return isPublic ? addedPublicFiles.has(fileName) : addedUserFiles.has(fileName);
  }

  async function addMaterialToProject(filePath: string, isPublic: boolean) {
    if (!selectedProject || (isPublic === false && !currentUsername)) return;

    try {
      const relativePath = isPublic
        ? `public/media/${filePath}`
        : `${currentUsername}/media/${filePath}`;

      const fileName = filePath.split('/').pop() || '';

      const response = await fetch(
        `/api/projects/${selectedProject.id}/materials`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            relativePath,
            fileName,
            fileType: 'file' // We'll need to determine this from the file
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

  async function toggleFolder(node: TreeNode, isPublic: boolean) {
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

  async function selectFolder(folderPath: string, isPublic: boolean) {
    selectedFolderPath = folderPath;
    loadingContents = true;
    try {
      const response = await fetch(`/api/media?level=${isPublic ? 'public' : 'user'}${folderPath ? `&folder=${encodeURIComponent(folderPath)}` : ''}`);
      if (response.ok) {
        const files = await response.json();
        // Filter to only show files, not folders
        currentFolderContents = files.filter((file: MediaFile) => file.type !== 'folder');
      } else {
        currentFolderContents = [];
      }
    } catch (err) {
      console.error('Error loading folder contents:', err);
      currentFolderContents = [];
    } finally {
      loadingContents = false;
    }
  }

  async function createFolder() {
    if (!newFolderName.trim()) return;

    try {
      const response = await fetch('/api/media', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          level: materialsTab,
          folderName: newFolderName.trim(),
          parentFolder: currentFolderPath
        })
      });

      if (response.ok) {
        // Refresh the current folder
        if (materialsTab === 'public') {
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

      <!-- Materials Tabs -->
      <div class="mb-6">
        <div class="flex rounded-lg bg-gray-100/50 p-1">
          <button
            class="flex-1 rounded-md px-4 py-2 transition-all duration-200"
            class:bg-white={materialsTab === 'public'}
            class:text-gray-900={materialsTab === 'public'}
            class:text-gray-600={materialsTab !== 'public'}
            onclick={() => (materialsTab = 'public')}
          >
            Public Media
          </button>
          <button
            class="flex-1 rounded-md px-4 py-2 transition-all duration-200"
            class:bg-white={materialsTab === 'user'}
            class:text-gray-900={materialsTab === 'user'}
            class:text-gray-600={materialsTab !== 'user'}
            onclick={() => (materialsTab = 'user')}
          >
            User Media
          </button>
        </div>
      </div>

      <!-- Tree View -->
      <div class="flex gap-4 h-[calc(100vh-200px)]">
        <!-- Tree Navigation -->
        <div class="w-80 bg-gray-50 rounded-lg p-4 overflow-y-auto">
          {#if materialsTab === 'public'}
            {#if loadingPublic}
              <div class="flex items-center justify-center py-4">
                <div class="animate-spin rounded-full border-2 border-blue-500 border-t-transparent w-6 h-6"></div>
                <span class="ml-2">Loading...</span>
              </div>
            {:else}
              <div class="space-y-1">
                <!-- Public Media Root -->
                <div class="flex items-center py-1 hover:bg-gray-100 rounded px-2">
                  <button
                    class="flex items-center mr-2 text-gray-500 hover:text-gray-700"
                    onclick={() => toggleFolder(publicTree, true)}
                  >
                    {#if publicTree.loading}
                      <div class="w-4 h-4 mr-1 animate-spin rounded-full border-2 border-blue-500 border-t-transparent"></div>
                    {:else}
                      <svg class="w-4 h-4 mr-1 transform transition-transform {publicTree.expanded ? 'rotate-90' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                      </svg>
                    {/if}
                  </button>
                  <span class="text-xl mr-2">📁</span>
                  <span class="text-sm font-medium">Public Media</span>
                  <div class="ml-auto flex gap-1">
                    <button
                      class="text-gray-400 hover:text-gray-600 p-1 rounded"
                      onclick={() => { currentFolderPath = ''; showCreateFolder = true; }}
                      title="Create folder"
                    >
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path>
                      </svg>
                    </button>
                  </div>
                </div>

                {#if publicTree.expanded && publicTree.children}
                  {#each publicTree.children.filter(n => n.type === 'folder') as node}
                    <div class="flex items-center py-1 hover:bg-gray-100 rounded px-2 ml-4">
                      <button
                        class="flex items-center mr-2 text-gray-500 hover:text-gray-700"
                        onclick={() => toggleFolder(node, true)}
                      >
                        {#if node.loading}
                          <div class="w-4 h-4 mr-1 animate-spin rounded-full border-2 border-blue-500 border-t-transparent"></div>
                        {:else}
                          <svg class="w-4 h-4 mr-1 transform transition-transform {node.expanded ? 'rotate-90' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                          </svg>
                        {/if}
                      </button>
                      <button
                        class="flex items-center flex-1 text-left {selectedFolderPath === node.path ? 'bg-blue-100' : ''}"
                        onclick={() => selectFolder(node.path, true)}
                      >
                        <span class="text-lg mr-2">📁</span>
                        <span class="text-sm">{node.name}</span>
                      </button>
                      <div class="ml-auto flex gap-1">
                        <button
                          class="text-gray-400 hover:text-gray-600 p-1 rounded"
                          onclick={(e) => { e.stopPropagation(); currentFolderPath = node.path; showCreateFolder = true; }}
                          title="Create subfolder"
                        >
                          <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path>
                          </svg>
                        </button>
                      </div>
                    </div>
                    {#if node.expanded && node.children}
                      {#each node.children.filter(n => n.type === 'folder') as child}
                        <div class="flex items-center py-1 hover:bg-gray-100 rounded px-2 ml-8">
                          <button
                            class="flex items-center mr-2 text-gray-500 hover:text-gray-700"
                            onclick={() => toggleFolder(child, true)}
                          >
                            {#if child.loading}
                              <div class="w-4 h-4 mr-1 animate-spin rounded-full border-2 border-blue-500 border-t-transparent"></div>
                            {:else}
                              <svg class="w-4 h-4 mr-1 transform transition-transform {child.expanded ? 'rotate-90' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                              </svg>
                            {/if}
                          </button>
                          <button
                            class="flex items-center flex-1 text-left"
                            onclick={() => selectFolder(child.path, true)}
                            class:bg-blue-100={selectedFolderPath === child.path}
                          >
                            <span class="text-lg mr-2">📁</span>
                            <span class="text-sm">{child.name}</span>
                          </button>
                        </div>
                      {/each}
                    {/if}
                  {/each}
                {/if}
              </div>
            {/if}
          {:else}
            {#if loadingUser}
              <div class="flex items-center justify-center py-4">
                <div class="animate-spin rounded-full border-2 border-blue-500 border-t-transparent w-6 h-6"></div>
                <span class="ml-2">Loading...</span>
              </div>
            {:else}
              <div class="space-y-1">
                <!-- User Media Root -->
                <div class="flex items-center py-1 hover:bg-gray-100 rounded px-2">
                  <button
                    class="flex items-center mr-2 text-gray-500 hover:text-gray-700"
                    onclick={() => toggleFolder(userTree, false)}
                  >
                    {#if userTree.loading}
                      <div class="w-4 h-4 mr-1 animate-spin rounded-full border-2 border-blue-500 border-t-transparent"></div>
                    {:else}
                      <svg class="w-4 h-4 mr-1 transform transition-transform {userTree.expanded ? 'rotate-90' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                      </svg>
                    {/if}
                  </button>
                  <span class="text-xl mr-2">📁</span>
                  <span class="text-sm font-medium">User Media</span>
                  <div class="ml-auto flex gap-1">
                    <button
                      class="text-gray-400 hover:text-gray-600 p-1 rounded"
                      onclick={() => { currentFolderPath = ''; showCreateFolder = true; }}
                      title="Create folder"
                    >
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path>
                      </svg>
                    </button>
                  </div>
                </div>

                {#if userTree.expanded && userTree.children}
                  {#each userTree.children as node}
                    <div class="flex items-center py-1 hover:bg-gray-100 rounded px-2 ml-4">
                      {#if node.type === 'folder'}
                        <button
                          class="flex items-center mr-2 text-gray-500 hover:text-gray-700"
                          onclick={() => toggleFolder(node, false)}
                        >
                          {#if node.loading}
                            <div class="w-4 h-4 mr-1 animate-spin rounded-full border-2 border-blue-500 border-t-transparent"></div>
                          {:else}
                            <svg class="w-4 h-4 mr-1 transform transition-transform {node.expanded ? 'rotate-90' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                            </svg>
                          {/if}
                        </button>
                        <span class="text-lg mr-2">📁</span>
                        <span class="text-sm">{node.name}</span>
                        <div class="ml-auto flex gap-1">
                          <button
                            class="text-gray-400 hover:text-gray-600 p-1 rounded"
                            onclick={() => { currentFolderPath = node.path; showCreateFolder = true; }}
                            title="Create subfolder"
                          >
                            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path>
                            </svg>
                          </button>
                        </div>
                      {:else}
                        <span class="text-lg mr-2">
                          {#if node.type === 'image'}
                            🖼️
                          {:else if node.type === 'video'}
                            🎥
                          {:else if node.type === 'audio'}
                            🎵
                          {:else}
                            📄
                          {/if}
                        </span>
                        <span class="text-sm">{node.name}</span>
                        {#if isMaterialInProject(node.path, false)}
                          <button
                            class="ml-auto bg-red-500 text-white rounded-full p-1 hover:bg-red-600"
                            onclick={() => {
                              const material = projectMaterials.find(m =>
                                m.relativePath === `${currentUsername}/media/${node.path}`
                              );
                              if (material) removeMaterialFromProject(material.id);
                            }}
                            title="Remove from project"
                          >
                            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                            </svg>
                          </button>
                        {:else}
                          <button
                            class="ml-auto bg-green-500 text-white rounded-full p-1 hover:bg-green-600"
                            onclick={() => addMaterialToProject(node.path, false)}
                            title="Add to project"
                          >
                            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path>
                            </svg>
                          </button>
                        {/if}
                      {/if}
                    </div>
                  {/each}
                {/if}
              </div>
            {/if}
          {/if}
        </div>

        <!-- Content Area -->
        <div class="flex-1 bg-white rounded-lg border p-4">
          <div class="text-center text-gray-500 py-8">
            Select a folder or file from the tree to view contents
          </div>
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
