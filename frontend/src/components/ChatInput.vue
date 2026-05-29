<template>
  <div class="input-area">
    <!-- Image preview -->
    <div v-if="imagePreview" class="image-preview-row">
      <div class="preview-thumb">
        <img :src="imagePreview" alt="Preview" />
        <button class="btn-remove-img" @click="removeImage" aria-label="移除图片">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M3 3l8 8M11 3l-8 8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
        </button>
      </div>
    </div>

    <form class="input-row" @submit.prevent="handleSend">
      <label class="btn-upload" :class="{ disabled }" aria-label="上传图片">
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none"><rect x="2" y="4" width="16" height="12" rx="2" stroke="currentColor" stroke-width="1.6"/><circle cx="7" cy="9" r="1.5" stroke="currentColor" stroke-width="1.3"/><path d="M2 14l5-4 3 2 3-3 5 5" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/></svg>
        <input type="file" accept="image/*" @change="onFileChange" :disabled="disabled" hidden />
      </label>

      <textarea
        ref="textareaEl"
        v-model="text"
        :placeholder="placeholder"
        :disabled="disabled"
        rows="1"
        @keydown.enter.exact="handleEnter"
        @input="autoResize"
      />

      <button type="submit" class="btn-send" :disabled="!canSend || disabled" aria-label="发送">
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none"><path d="M2 10l16-8-8 16-2-6-6-2z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/></svg>
      </button>
    </form>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'

const props = defineProps({
  disabled: Boolean,
  pendingQuestion: String,
})

const emit = defineEmits(['send'])

const text = ref('')
const imageFile = ref(null)
const imagePreview = ref(null)
const textareaEl = ref(null)

const placeholder = computed(() => {
  if (props.disabled) return '小宠正在回复中...'
  if (props.pendingQuestion) return '请回答小宠的问题...'
  return '描述宠物的症状，小宠来帮你分析...'
})

const canSend = computed(() => text.value.trim() || imageFile.value)

function handleEnter(e) {
  if (!e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

function autoResize() {
  const el = textareaEl.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 120) + 'px'
}

function onFileChange(e) {
  const file = e.target.files[0]
  if (!file) return
  imageFile.value = file
  const reader = new FileReader()
  reader.onload = () => { imagePreview.value = reader.result }
  reader.readAsDataURL(file)
}

function removeImage() {
  imageFile.value = null
  imagePreview.value = null
}

function handleSend() {
  if (!canSend.value || props.disabled) return
  emit('send', { text: text.value.trim(), imageFile: imageFile.value })
  text.value = ''
  imageFile.value = null
  imagePreview.value = null
  nextTick(() => {
    if (textareaEl.value) {
      textareaEl.value.style.height = 'auto'
    }
  })
}

// Focus on mount
defineExpose({ focus: () => textareaEl.value?.focus() })
</script>

<style scoped>
.input-area {
  padding: 16px 24px 20px;
  background: var(--bg-card);
  border-top: 1px solid var(--border-light);
  flex-shrink: 0;
}

.image-preview-row {
  margin-bottom: 10px;
}
.preview-thumb {
  position: relative;
  display: inline-block;
}
.preview-thumb img {
  width: 64px; height: 64px;
  object-fit: cover;
  border-radius: var(--radius-sm);
  border: 2px solid var(--border);
}
.btn-remove-img {
  position: absolute;
  top: -6px; right: -6px;
  width: 22px; height: 22px;
  border-radius: 50%;
  background: var(--bg-card);
  border: 1px solid var(--border);
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--shadow-sm);
}
.btn-remove-img:hover { background: var(--red-100); color: var(--red-500); }

.input-row {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  background: var(--bg-app);
  border-radius: var(--radius-lg);
  padding: 8px 10px;
  border: 1.5px solid transparent;
  transition: border-color var(--duration-fast), box-shadow var(--duration-fast);
}
.input-row:focus-within {
  border-color: var(--green-300);
  box-shadow: 0 0 0 3px rgba(93, 138, 91, 0.1);
}

.btn-upload {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px; height: 38px;
  flex-shrink: 0;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  cursor: pointer;
  transition: color var(--duration-fast), background var(--duration-fast);
}
.btn-upload:hover:not(.disabled) { color: var(--green-500); background: var(--green-100); }
.btn-upload.disabled { opacity: 0.35; cursor: not-allowed; }

textarea {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 15px;
  line-height: 1.5;
  resize: none;
  padding: 8px 4px;
  color: var(--text-primary);
  max-height: 120px;
  min-height: 24px;
}
textarea::placeholder { color: #bfb9a8; }
textarea:disabled { opacity: 0.5; }

.btn-send {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px; height: 38px;
  flex-shrink: 0;
  border-radius: 50%;
  background: var(--green-500);
  color: #fff;
  transition: all var(--duration-fast) var(--ease-out);
  box-shadow: 0 2px 8px rgba(93, 138, 91, 0.25);
}
.btn-send:hover:not(:disabled) {
  background: var(--green-700);
  transform: scale(1.05);
  box-shadow: 0 4px 14px rgba(93, 138, 91, 0.35);
}
.btn-send:active:not(:disabled) {
  transform: scale(0.95);
}
.btn-send:disabled {
  background: var(--border);
  box-shadow: none;
  cursor: not-allowed;
}
.btn-send:disabled svg { opacity: 0.4; }
</style>
