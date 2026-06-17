from ollama import Client
client = Client(
  host='http://192.168.58.137:3039'
)
response = client.chat(model='qwen3.6:27b', keep_alive=600, messages=[
  {
    'role': 'user',
    'content': 'Why is the sky blue?',
  },
])
print(response.message.content)

# Pass in the path to the image
path = input('Please enter the path to the image: ')

# You can also pass in base64 encoded image data
# img = base64.b64encode(Path(path).read_bytes()).decode()
# or the raw bytes
# img = Path(path).read_bytes()
from ollama import Client
client = Client(
  host='http://192.168.58.137:3039'
)

response = client.chat(
  model='qwen3.6:27b',
  messages=[
    {
      'role': 'user',
      'content': 'Thông tin trong hình là gì?',
      'images': [path],
    }
  ],
)

print(response.message.content)
