with open('temp2.txt', 'r') as f:
    c = f.read()
print('v-for key on template:', 'v-for="flag in selectedEvent.flags" :key=' in c)
print('&& instead of and:', 'selectedEvent.flags && selectedEvent' in c)
print('</template> count:', c.count('</template>'))