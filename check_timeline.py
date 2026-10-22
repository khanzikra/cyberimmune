with open('temp_timeline.txt', 'r') as f:
    content = f.read()
print('v-for key on template:', 'v-for="flag in selectedEvent.flags" :key=' in content)
print('&& instead of and:', 'selectedEvent.flags && selectedEvent' in content)
print('</template> count:', content.count('</template>'))