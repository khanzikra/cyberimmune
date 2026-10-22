import sys
data = sys.stdin.buffer.read()
print('v-for key:', b'v-for="flag in selectedEvent.flags" :key=' in data)
print('&&:', b'selectedEvent.flags && selectedEvent' in data)
print('</template>:', data.count(b'</template>'))