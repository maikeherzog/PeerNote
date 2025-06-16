import socket
import threading
import json
import hashlib
import time
from datetime import datetime
import uuid
import random

class Comment:
  def __init__(self, author, content):
    self.id = str(uuid.uuid4())
    self.author = author
    self.content = content