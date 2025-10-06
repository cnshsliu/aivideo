<script lang="ts">
  import { onMount } from 'svelte';
  import { addColumn, dropColumn, modifyColumn, addConstraint, dropConstraint } from '$lib/schemaUtils';
  
  let result = '';
  let error = '';
  let isLoading = false;
  
  // Function to add a test column
  async function addTestColumn() {
    isLoading = true;
    error = '';
    result = '';
    
    try {
      const response = await addColumn('project', 'test_column', 'TEXT', 'default_value', true);
      result = JSON.stringify(response, null, 2);
    } catch (err: any) {
      error = err.message || 'An error occurred';
    } finally {
      isLoading = false;
    }
  }
  
  // Function to drop the test column
  async function dropTestColumn() {
    isLoading = true;
    error = '';
    result = '';
    
    try {
      const response = await dropColumn('project', 'test_column');
      result = JSON.stringify(response, null, 2);
    } catch (err: any) {
      error = err.message || 'An error occurred';
    } finally {
      isLoading = false;
    }
  }
  
  // Function to add a test constraint
  async function addTestConstraint() {
    isLoading = true;
    error = '';
    result = '';
    
    try {
      const response = await addConstraint('project', 'test_constraint', 'unique', 'name');
      result = JSON.stringify(response, null, 2);
    } catch (err: any) {
      error = err.message || 'An error occurred';
    } finally {
      isLoading = false;
    }
  }
  
  // Function to drop the test constraint
  async function dropTestConstraint() {
    isLoading = true;
    error = '';
    result = '';
    
    try {
      const response = await dropConstraint('project', 'test_constraint');
      result = JSON.stringify(response, null, 2);
    } catch (err: any) {
      error = err.message || 'An error occurred';
    } finally {
      isLoading = false;
    }
  }
</script>

<div class="p-8 max-w-4xl mx-auto">
  <h1 class="text-3xl font-bold mb-6">Schema Modification Tool Test</h1>
  
  <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
    <div class="bg-white rounded-lg shadow p-6">
      <h2 class="text-xl font-semibold mb-4">Add Column</h2>
      <p class="text-gray-600 mb-4">Add a test column to the project table</p>
      <button 
        class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded disabled:opacity-50"
        on:click={addTestColumn}
        disabled={isLoading}
      >
        {isLoading ? 'Processing...' : 'Add Test Column'}
      </button>
    </div>
    
    <div class="bg-white rounded-lg shadow p-6">
      <h2 class="text-xl font-semibold mb-4">Drop Column</h2>
      <p class="text-gray-600 mb-4">Remove the test column from the project table</p>
      <button 
        class="bg-red-500 hover:bg-red-700 text-white font-bold py-2 px-4 rounded disabled:opacity-50"
        on:click={dropTestColumn}
        disabled={isLoading}
      >
        {isLoading ? 'Processing...' : 'Drop Test Column'}
      </button>
    </div>
    
    <div class="bg-white rounded-lg shadow p-6">
      <h2 class="text-xl font-semibold mb-4">Add Constraint</h2>
      <p class="text-gray-600 mb-4">Add a unique constraint on the name column</p>
      <button 
        class="bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded disabled:opacity-50"
        on:click={addTestConstraint}
        disabled={isLoading}
      >
        {isLoading ? 'Processing...' : 'Add Test Constraint'}
      </button>
    </div>
    
    <div class="bg-white rounded-lg shadow p-6">
      <h2 class="text-xl font-semibold mb-4">Drop Constraint</h2>
      <p class="text-gray-600 mb-4">Remove the test constraint</p>
      <button 
        class="bg-yellow-500 hover:bg-yellow-700 text-white font-bold py-2 px-4 rounded disabled:opacity-50"
        on:click={dropTestConstraint}
        disabled={isLoading}
      >
        {isLoading ? 'Processing...' : 'Drop Test Constraint'}
      </button>
    </div>
  </div>
  
  {#if error}
    <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6">
      <strong>Error:</strong> {error}
    </div>
  {/if}
  
  {#if result}
    <div class="bg-gray-100 border border-gray-400 rounded p-4">
      <h3 class="text-lg font-semibold mb-2">Response:</h3>
      <pre class="whitespace-pre-wrap text-sm">{result}</pre>
    </div>
  {/if}
  
  <div class="mt-8 bg-blue-50 border border-blue-200 rounded p-4">
    <h3 class="text-lg font-semibold mb-2">How to use the Schema Modification Tool</h3>
    <ul class="list-disc pl-5 space-y-2">
      <li>Use the buttons above to test schema modifications</li>
      <li>The tool allows you to add/drop columns and constraints dynamically</li>
      <li>All operations are performed directly on the PostgreSQL database</li>
      <li>Check the response section to see the results of each operation</li>
    </ul>
  </div>
</div>

<style>
  button:disabled {
    cursor: not-allowed;
  }
</style>
