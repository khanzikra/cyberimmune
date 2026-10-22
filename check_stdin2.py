import sys
data = sys.stdin.read()
print('v-for key:', 'v-for="flag in selectedEvent.flags" :key=' in data)
print('&&:', 'selectedEvent.flags && selectedEvent' in data)
print('</template>:', data.count('</template>'))