with open('temp2.txt', 'rb') as f:
    c = f.read()
print('HEAD - v-for key:', b'v-for="flag in selectedEvent.flags" :key=' in c)
print('HEAD - &&:', b'selectedEvent.flags && selectedEvent' in c)
print('HEAD - </template>:', c.count(b'</template>'))