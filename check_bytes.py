with open('frontend/src/pages/timeline.vue', 'rb') as f:
    c = f.read()
print('Working dir - v-for key:', b'v-for="flag in selectedEvent.flags" :key=' in c)
print('Working dir - &&:', b'selectedEvent.flags && selectedEvent' in c)
print('Working dir - </template>:', c.count(b'</template>'))