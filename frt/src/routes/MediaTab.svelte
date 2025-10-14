<script lang="ts">
  import { onMount } from 'svelte';

  function focusInput(node: HTMLInputElement) {
    node.focus();
    node.select();
  }

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

  let {
    selectedFile,
    uploadLevel = $bindable('public'),
    selectedProject,
    isUploading = $bindable(false),
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
    onUpload?: (options: { level: string; folderPath: string }) => void;
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

  let publicTree = $state<TreeNode>({
    name: 'Public Media',
    type: 'folder',
    path: '',
    children: [],
    expanded: true
  });
  let userTree = $state<TreeNode>({
    name: 'User Media',
    type: 'folder',
    path: '',
    children: [],
    expanded: true
  });

  import TreeNode from '$lib/components/TreeNode.svelte';
  let loadingPublicMedia = $state(false);
  let loadingUserMedia = $state(false);
  let isSelecting = $state(false);
  let selectedMedia = $state<MediaFile[]>([]);
  let isDeleting = $state(false);
  let showCreateFolder = $state(false);
  let newFolderName = $state('');
  let currentFolderPath = $state('');
  let currentFolderFiles = $state<MediaFile[]>([]);
  let selectedFolderNode = $state<TreeNode | null>(null);
  let currentIsPublic = $state(true);
  let renamingFile = $state<MediaFile | null>(null);
  let newFileName = $state('');
  let lastFolderKey = 'mediaTab_lastFolder';

  async function loadPublicMediaFiles(folderPath = '') {
    loadingPublicMedia = true;
    try {
      console.log('🌐 [CLIENT] Loading public media files...');
      const response = await fetch(
        `/api/media?level=public${folderPath ? `&folder=${encodeURIComponent(folderPath)}` : ''}`
      );
      console.log('🌐 [CLIENT] Public response status:', response.status);
      console.log('🌐 [CLIENT] Public response ok:', response.ok);

      if (response.ok) {
        const data = await response.json();
        console.log('🌐 [CLIENT] Public media data:', data);
        updateTree(publicTree, folderPath, data);

        // If this is for the current folder, update the content area
        if (folderPath === currentFolderPath) {
          currentFolderFiles = data.filter(
            (file: MediaFile) => file.type !== 'folder'
          );
        }
      } else {
        console.error(
          '🌐 [CLIENT] Failed to load public media files:',
          await response.text()
        );
      }
    } catch (err) {
      console.error('🌐 [CLIENT] Error loading public media files:', err);
    } finally {
      loadingPublicMedia = false;
    }
  }

  async function loadUserMediaFiles(folderPath = '') {
    loadingUserMedia = true;
    try {
      console.log('🌐 [CLIENT] Loading user media files...');
      const response = await fetch(
        `/api/media?level=user${folderPath ? `&folder=${encodeURIComponent(folderPath)}` : ''}`
      );
      console.log('🌐 [CLIENT] Response status:', response.status);
      console.log('🌐 [CLIENT] Response ok:', response.ok);

      if (response.ok) {
        const data = await response.json();
        console.log('🌐 [CLIENT] User media data:', data);
        updateTree(userTree, folderPath, data);

        // If this is for the current folder, update the content area
        if (folderPath === currentFolderPath) {
          currentFolderFiles = data.filter(
            (file: MediaFile) => file.type !== 'folder'
          );
        }
      } else {
        console.error(
          '🌐 [CLIENT] Failed to load user media files:',
          await response.text()
        );
      }
    } catch (err) {
      console.error('🌐 [CLIENT] Error loading user media files:', err);
    } finally {
      loadingUserMedia = false;
    }
  }

  async function loadFolderContent(node: TreeNode, isPublic: boolean) {
    selectedFolderNode = node;
    currentFolderPath = node.path;

    // Set the upload level to match the tree selection
    uploadLevel = isPublic ? 'public' : 'user';
    currentIsPublic = isPublic;

    // Save the current folder to localStorage
    saveLastFolder(isPublic, node.path);

    try {
      const level = isPublic ? 'public' : 'user';
      const folderParam = node.path
        ? `&folder=${encodeURIComponent(node.path)}`
        : '';
      const response = await fetch(`/api/media?level=${level}${folderParam}`);

      if (response.ok) {
        const data = await response.json();
        currentFolderFiles = data.filter(
          (file: MediaFile) => file.type !== 'folder'
        );
      } else {
        console.error('Failed to load folder content:', await response.text());
        currentFolderFiles = [];
      }
    } catch (err) {
      console.error('Error loading folder content:', err);
      currentFolderFiles = [];
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

  async function loadFolderContentOnly(node: TreeNode, isPublic: boolean) {
    // Load folder content into the right panel without toggling expand
    await loadFolderContent(node, isPublic);
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
          await loadPublicMediaFiles(node.path);
        } else {
          await loadUserMediaFiles(node.path);
        }
      }
    }
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
          await loadPublicMediaFiles(currentFolderPath);
        } else {
          await loadUserMediaFiles(currentFolderPath);
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

  async function deleteFile(file: MediaFile) {
    isDeleting = true;
    try {
      console.log('🗑️ [CLIENT] Deleting media file:', file.name);
      const response = await fetch('/api/media', {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          level: currentIsPublic ? 'public' : 'user',
          files: [file.name]
        })
      });

      if (response.ok) {
        const result = await response.json();
        console.log('🗑️ [CLIENT] Delete result:', result);
        // Reload current folder content
        if (selectedFolderNode) {
          await loadFolderContent(selectedFolderNode, currentIsPublic);
        }
        // Remove from selection if selected
        selectedMedia = selectedMedia.filter((f) => f.name !== file.name);
      } else {
        console.error(
          '🗑️ [CLIENT] Failed to delete media:',
          await response.text()
        );
        alert('Failed to delete media file. Please try again.');
      }
    } catch (err) {
      console.error('🗑️ [CLIENT] Error deleting media:', err);
      alert('An error occurred while deleting media file.');
    } finally {
      isDeleting = false;
    }
  }

  async function deleteSelectedMedia() {
    if (selectedMedia.length === 0) return;

    isDeleting = true;
    try {
      console.log(
        '🗑️ [CLIENT] Deleting media files:',
        selectedMedia.map((f) => f.name)
      );
      const response = await fetch('/api/media', {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          level: currentIsPublic ? 'public' : 'user',
          files: selectedMedia.map((f) => f.name)
        })
      });

      if (response.ok) {
        const result = await response.json();
        console.log('🗑️ [CLIENT] Delete result:', result);
        // Reload current folder content
        if (selectedFolderNode) {
          await loadFolderContent(selectedFolderNode, currentIsPublic);
        }
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

  function startRenameFile(file: MediaFile) {
    renamingFile = file;
    newFileName = file.name;
  }

  async function confirmRenameFile() {
    if (!renamingFile || !newFileName.trim()) return;

    // Preserve the original file extension
    const originalExt = renamingFile.name.includes('.')
      ? renamingFile.name.substring(renamingFile.name.lastIndexOf('.'))
      : '';
    let finalNewName = newFileName.trim();

    // If the new name doesn't have an extension, add the original one
    if (!finalNewName.includes('.')) {
      finalNewName += originalExt;
    }
    // If the new name has a different extension, replace it with the original
    else if (originalExt && !finalNewName.endsWith(originalExt)) {
      finalNewName = finalNewName.substring(0, finalNewName.lastIndexOf('.')) + originalExt;
    }

    try {
      const response = await fetch('/api/media', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          level: currentIsPublic ? 'public' : 'user',
          oldName: renamingFile.name,
          newName: finalNewName,
          folderPath: currentFolderPath
        })
      });

      if (response.ok) {
        const result = await response.json();
        console.log('✏️ [CLIENT] Rename result:', result);
        // Reload current folder content
        if (selectedFolderNode) {
          await loadFolderContent(selectedFolderNode, currentIsPublic);
        }
        // Update selection if the renamed file was selected
        selectedMedia = selectedMedia.map((f) =>
          f.name === renamingFile!.name ? { ...f, name: result.finalName } : f
        );
        renamingFile = null;
        newFileName = '';
      } else {
        const error = await response.json();
        alert(error.message || 'Failed to rename file');
      }
    } catch (err) {
      console.error('✏️ [CLIENT] Error renaming file:', err);
      alert('An error occurred while renaming the file.');
    }
  }

  function cancelRename() {
    renamingFile = null;
    newFileName = '';
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

  onMount(() => {
    // Load the media trees first
    Promise.all([
      loadPublicMediaFiles(),
      loadUserMediaFiles()
    ]).then(() => {
      // Then try to restore the last folder
      restoreLastFolder();
    });

    // Listen for media upload completion events
    const handleMediaUploadComplete = (event: CustomEvent) => {
      const { level } = event.detail;
      // After upload, refresh current folder content instead of entire tree
      if (
        selectedFolderNode &&
        ((level === 'public' && uploadLevel === 'public') ||
          (level === 'user' && uploadLevel === 'user'))
      ) {
        loadFolderContent(selectedFolderNode, level === 'public');
      } else {
        // Fallback: refresh the tree if no current folder selected
        if (level === 'public') {
          loadPublicMediaFiles();
        } else if (level === 'user') {
          loadUserMediaFiles();
        }
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
    <div id="upload-area" class="flex gap-4">
      <!-- Upload Section -->
      <div
        class="rounded-lg border-2 border-dashed border-gray-300 p-6 text-center transition-colors hover:border-blue-400 min-h-[10rem]"
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

        
      </div>

      <!-- Upload Options -->
      <div
        class="space-y-4 {selectedFile ? '' : 'opacity-0 pointer-events-none'}"
      >
<div
          class="mt-4 rounded-lg bg-blue-50 p-3 {selectedFile
            ? ''
            : 'opacity-0 pointer-events-none'}"
        >
          <span class="text-sm text-blue-800"
            >{selectedFile ? selectedFile.name : ''}</span
          >
        </div>

        <button
          onclick={() =>
            onUpload?.({ level: currentIsPublic ? 'public' : 'user', folderPath: currentFolderPath })}
          disabled={isUploading || !selectedFolderNode}
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
    </div>

    <!-- Media Browser -->

    <div class="mt-8">
      <div class="mb-4 text-sm text-gray-600">
        {#if selectedFolderNode}
          {currentIsPublic ? 'Public Media' : 'User Media'}{#if currentFolderPath} / {currentFolderPath.split('/').join(' / ')}{/if}
        {:else}
          Select a folder
        {/if}
      </div>
      <div class="flex gap-4 h-[calc(100vh-300px)]">
        <!-- Tree Navigation -->
        <div class="w-80 bg-gray-50 rounded-lg p-4 overflow-y-auto">
          {#if loadingPublicMedia}
            <div class="flex items-center justify-center py-4">
              <div
                class="animate-spin rounded-full border-2 border-blue-500 border-t-transparent w-6 h-6"
              ></div>
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
                isPublic ? loadPublicMediaFiles() : loadUserMediaFiles()}
            />
          {/if}
          {#if loadingUserMedia}
            <div class="flex items-center justify-center py-4">
              <div
                class="animate-spin rounded-full border-2 border-blue-500 border-t-transparent w-6 h-6"
              ></div>
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
                isPublic ? loadPublicMediaFiles() : loadUserMediaFiles()}
            />
          {/if}
        </div>

        <!-- Content Area -->
        <div class="flex-1 bg-white rounded-lg border p-4 overflow-y-auto">
          {#if selectedFolderNode}
            <div class="mb-4">
              <h3 class="text-lg font-semibold">{selectedFolderNode.name}</h3>
              <p class="text-sm text-gray-500">
                {currentFolderFiles.length} items
              </p>
            </div>

            {#if currentFolderFiles.length > 0}
              <div
                class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4"
              >
                {#each currentFolderFiles as file}
                  <div
                    class="group relative border rounded-lg p-2 hover:bg-gray-50 cursor-pointer transition-colors {selectedMedia.some(
                      (m) => m.name === file.name
                    )
                      ? 'ring-2 ring-blue-500'
                      : ''}"
                    role="button"
                    tabindex="0"
                    onclick={() => toggleMediaSelection(file)}
                    onkeydown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        toggleMediaSelection(file);
                      }
                    }}
                    ondblclick={() => startRenameFile(file)}
                  >
                    <button
                      class="absolute top-1 right-1 z-10 bg-red-500 text-white rounded-full w-6 h-6 flex items-center justify-center hover:bg-red-600 transition-colors opacity-0 group-hover:opacity-100"
                      onclick={(e) => {
                        e.stopPropagation();
                        deleteFile(file);
                      }}
                      disabled={isDeleting}
                      title="Delete file"
                    >
                      {#if isDeleting}
                        <div class="w-3 h-3 border border-white border-t-transparent rounded-full animate-spin"></div>
                      {:else}
                        ×
                      {/if}
                    </button>
                    <div
                      class="aspect-square flex items-center justify-center bg-gray-100 rounded mb-2 group"
                    >
                      {#if file.type === 'image' && file.url}
                       <div class="relative w-full h-full">
                        <img
                          src={file.url}
                          alt={file.name}
                          class="w-full h-full object-cover rounded"
                        /><div class="absolute inset-0 flex items-center justify-center bg-black/20 rounded opacity-0 group-hover:opacity-100 transition-opacity">
                              <button
                                class="bg-white/90 text-black rounded-full w-8 h-8 flex items-center justify-center hover:bg-white"
                                onclick={(e) => {
                                  e.stopPropagation();
                                  onPreviewMedia({
                                    type: 'image',
                                    url: file.url!,
                                    name: file.name
                                  });
                                }}
                              >
                                👁️
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
                              onclick={(e) => {
                                e.stopPropagation();
                                onPreviewMedia({
                                  type: 'video',
                                  url: file.url!,
                                  name: file.name
                                });
                              }}
                            ></video>
                            <div class="absolute inset-0 flex items-center justify-center bg-black/20 rounded opacity-0 group-hover:opacity-100 transition-opacity">
                              <button
                                class="bg-white/90 text-black rounded-full w-8 h-8 flex items-center justify-center hover:bg-white"
                                onclick={(e) => {
                                  e.stopPropagation();
                                  onPreviewMedia({
                                    type: 'video',
                                    url: file.url!,
                                    name: file.name
                                  });
                                }}
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
                          {getMediaIcon(file.type)}
                        </span>
                      {/if}
                    </div>
                    {#if renamingFile && renamingFile.name === file.name}
                      <input
                        type="text"
                        bind:value={newFileName}
                        class="text-xs w-full px-1 py-0.5 border rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                        onkeydown={(e) => {
                          if (e.key === 'Enter') confirmRenameFile();
                          if (e.key === 'Escape') cancelRename();
                        }}
                        use:focusInput
                      />
                    {:else}
                      <div class="text-xs truncate" title={file.name}>
                        {file.name}
                      </div>
                    {/if}
                    <div class="text-xs text-gray-500">
                      {formatFileSize(file.size)}
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
        <div
          class="fixed inset-0 z-60 flex items-center justify-center bg-black/50 backdrop-blur-sm"
        >
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
                onclick={() => {
                  showCreateFolder = false;
                  newFolderName = '';
                }}
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
</div>
