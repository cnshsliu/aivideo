<script lang="ts">
  interface TreeNode {
    name: string;
    type: string;
    path: string;
    children?: TreeNode[];
    expanded?: boolean;
    loading?: boolean;
  }

  interface Props {
    node: TreeNode;
    isPublic: boolean;
    depth?: number;
    selectedNode: TreeNode | null;
    onToggle: (node: TreeNode, isPublic: boolean) => void;
    onLoadContent: (node: TreeNode, isPublic: boolean) => void;
    onCreateFolder: (path: string, isPublic: boolean) => void;
    onRefresh: (isPublic: boolean) => void;
  }

  let { node, isPublic, depth = 0, selectedNode, onToggle, onLoadContent, onCreateFolder, onRefresh }: Props = $props();
</script>

<div class="flex items-center py-1 hover:bg-gray-100 rounded px-2 {node === selectedNode ? 'bg-blue-200' : ''} {depth === 0 ? '' : `ml-${Math.min(depth * 4, 16)}`}">
  <button
    class="flex items-center mr-2 text-gray-500 hover:text-gray-700"
    onclick={() => onToggle(node, isPublic)}
  >
    {#if node.loading}
      <div class="w-4 h-4 mr-1 animate-spin rounded-full border-2 border-blue-500 border-t-transparent"></div>
    {:else}
      <svg class="w-4 h-4 mr-1 transform transition-transform {node.expanded ? 'rotate-90' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
      </svg>
    {/if}
  </button>
  <span class="{depth === 0 ? 'text-xl' : 'text-lg'} mr-2">📁</span>
  <span
    class="text-sm font-medium cursor-pointer hover:text-blue-600"
    onclick={() => onLoadContent(node, isPublic)}
    ondblclick={() => onToggle(node, isPublic)}
  >{node.name}</span>
  {#if depth > 0}
    <div class="ml-auto flex gap-1">
      <button
        class="text-gray-400 hover:text-gray-600 p-1 rounded"
        onclick={() => onCreateFolder(node.path, isPublic)}
        title="Create subfolder"
      >
        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path>
        </svg>
      </button>
    </div>
  {:else if node.name === 'Public Media' || node.name === 'User Media'}
    <div class="ml-auto flex gap-1">
      <button
        class="text-gray-400 hover:text-gray-600 p-1 rounded"
        onclick={() => onCreateFolder('', isPublic)}
        title="Create folder"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path>
        </svg>
      </button>
      <button
        class="text-gray-400 hover:text-gray-600 p-1 rounded"
        onclick={() => onRefresh(isPublic)}
        title="Refresh"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
        </svg>
      </button>
    </div>
  {/if}
</div>
{#if node.expanded && node.children}
  {#each node.children as child}
    <svelte:self node={child} {isPublic} depth={depth + 1} {selectedNode} {onToggle} {onLoadContent} {onCreateFolder} {onRefresh} />
  {/each}
{/if}
