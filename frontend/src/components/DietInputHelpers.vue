<template>
  <div class="helpers">
    <button class="helper-btn" @click="triggerImageUpload" title="上传商品粮包装照,营养师会用 OCR 提取保证成分">
      <span class="icon">📷</span>
      <span>上传包装照</span>
    </button>
    <button class="helper-btn" @click="insertHomemadeTemplate" title="在对话框插入自制饮食模板">
      <span class="icon">🍱</span>
      <span>自制饮食模板</span>
    </button>
    <button class="helper-btn" @click="insertProfileTemplate" title="在对话框插入宠物档案模板">
      <span class="icon">🐾</span>
      <span>填档案</span>
    </button>
  </div>
</template>

<script setup>
const emit = defineEmits(['upload-image', 'insert-text'])

function triggerImageUpload() {
  emit('upload-image')
}

function insertHomemadeTemplate() {
  emit('insert-text',
`我家狗每天吃:
- 鸡胸肉 200g
- 白米饭 100g
- 南瓜 50g
请评估营养是否均衡。`)
}

function insertProfileTemplate() {
  emit('insert-text',
`我家是 10kg 的拉布拉多,3 岁,已绝育,无已知疾病,无食物过敏。`)
}
</script>

<style scoped>
.helpers {
  display: flex;
  gap: 8px;
  padding: 8px 12px 4px;
  flex-wrap: wrap;
}

.helper-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-full);
  font-family: var(--font-body);
  font-size: 12px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.helper-btn:hover {
  background: var(--green-100);
  color: var(--green-700);
  border-color: var(--green-300);
  transform: translateY(-1px);
}

.helper-btn .icon {
  font-size: 14px;
}
</style>
