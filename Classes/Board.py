import socket
import threading
import json
import hashlib
import time
from datetime import datetime, timedelta
import uuid
from collections import defaultdict

import random

from Classes.Card import Card

class Board:
    def __init__(self, title: str, keywords: set[str]):
        self.entries: defaultdict = defaultdict()  # card_id -> {card, timestamp, user_id, acronym}

        # board id
        self.board_id: str = str(uuid.uuid4())

        # board title
        self.title: str = title

        #
        self.keywords: set[str] = keywords
        self.card_references: dict[tuple[str, str], Card] = {}

        self.not_allowed_to_write = []

        # mutex lock, allowing parallelism
        self.lock = threading.Lock()

    def get_board_id(self):
        return self.board_id

    def get_title(self):
        return self.title

    def get_keywords(self):
        return self.keywords

    def get_card_references(self):
        return self.card_references

    def get_not_allowed_to_write(self):
        return self.not_allowed_to_write

    def soft_state_update(self, card_id, user_id):
        '''
        Update the timestamp of an soft state entry in the data storage of the board.
        The timestamp is only updated if the card_id exist and the user id matches the entry.
        :param card_id: id of the card
        :param user_id: id of the user
        :return: None
        '''
        now = datetime.utcnow()

        if card_id in self.entries.keys():
            with self.lock:
                # get card id data
                card_data, _timestamp, user_id_ref, acronym = self.entries[card_id]
                # check whether user id is the same
                if user_id_ref == user_id:
                    self.entries[card_id] = {
                        'card': card_data,
                        'timestamp': now,
                        'user_id': user_id,
                        'acronym': acronym
                    }

        # missing state, maybe inform peer about change

    def add_new_card(self, card_id, card_data, user_id, acronym):
        '''
               Add a new Card to the storage of the board.
               The timestamp is only updated if the card_id exist and the user id matches the entry.
               :param card_id: id of the card
               :param user_id: id of the user
               :param card_data: data of the card
               :param acronym: user acronym
               :return: None
               '''
        now = datetime.utcnow()
        with self.lock:
            self.entries[card_id] = {
                'card': card_data,
                'timestamp': now,
                'user_id': user_id,
                'acronym': acronym
            }
        print(f"Card {card_id} updated by {user_id} at {now}")

    def evict_old_entries(self, max_age: timedelta):
        '''
        Updates data_storage and evicts all entries being too old.
        :param max_age: timedelta object containing the maximum age
        :return:
        '''
        # sollte gecalled werden nachdem man karten updaten bzw bevor man welche zurück gibt
        cutoff = datetime.utcnow() - max_age
        with self.lock:
            to_delete = [card_id for card_id, data in self.entries.items() if data['timestamp'] < cutoff]
            for card_id in to_delete:
                del self.entries[card_id]
                print(f"Card {card_id} evicted due to staleness")

    def set_title(self, title):
        self.title = title

    def set_keywords(self, keywords: set[str]):
        self.keywords = keywords

    def add_keyword(self, keyword: str):
        self.keywords.add(keyword)

    def get_board(self):
        '''
        TODO: nicht fertig implementiert
        Idea: Return all valid card references, so that the peer is able to request the content of those.
        :return:
        '''

    def query_matches(self, keywords: set[str]) -> bool:
        '''
        Matches given keywords with safed keywords describing the board.
        If at least one key matches one keyword in the internal keyword set, true is returned
        :param keywords: keys to be matched against
        :return: 'True' if at least one key matche, otherwise 'False'
        '''
        for key in keywords:
            if key in self.keywords:
                return True
        return False


    def has_meta_ref(self, node_id, title) -> bool:
        return self.card_references.get((node_id, title)) is not None


    def get_reference(self, node_id, title) -> Card | None:
        return self.card_references.get((node_id, title))

    def update_reference(self, node_id, title, host, port):
        if self.has_meta_ref(node_id, title):
            self.card_references.get((node_id, title)).update_timestamp()
        else:
            self.card_references[(node_id, title)] = Card(title, node_id, host, port)
    def add_not_allowed_to_write(self, user_id):
        self.not_allowed_to_write.append(user_id)


