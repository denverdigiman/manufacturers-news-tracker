<template>
  <div class="directory-tree select-none">
    <TreeNodeItem
      v-for="node in nodes"
      :key="node.path"
      :node="node"
      :activeNotePath="activeNotePath"
      @navigate="$emit('navigate', $event)"
    />
  </div>
</template>

<script setup>
import TreeNodeItem from "./TreeNodeItem.vue";

defineProps({
  nodes: { type: Array, default: () => [] },
  activeNotePath: { type: String, default: null },
});

defineEmits(["navigate"]);
</script>
