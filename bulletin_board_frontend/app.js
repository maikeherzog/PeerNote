// Multi-Board Bulletin Board Manager
class BulletinBoardManager {
  constructor() {
    this.boards = this.loadBoards();
    this.currentBoardId = this.loadCurrentBoard();
    this.currentEditId = null;
    
    this.initializeEventListeners();
    this.renderBoardTabs();
    this.loadCurrentBoardCards();
  }

  // Daten laden und speichern
  loadBoards() {
    const saved = localStorage.getItem('bulletinBoards');
    if (saved) {
      return JSON.parse(saved);
    }
    
    // Standard Board "Sommer" erstellen (wird mit cards.json gefüllt)
    const defaultBoard = {
      id: 'board-sommer',
      name: 'Sommer',
      cards: [],
      useJsonFile: true // Flag für JSON-Datei
    };
    
    return [defaultBoard];
  }

  saveBoards() {
    localStorage.setItem('bulletinBoards', JSON.stringify(this.boards));
  }

  loadCurrentBoard() {
    const saved = localStorage.getItem('currentBoardId');
    return saved || (this.boards.length > 0 ? this.boards[0].id : null);
  }

  saveCurrentBoard() {
    localStorage.setItem('currentBoardId', this.currentBoardId);
  }

  getCurrentBoard() {
    return this.boards.find(board => board.id === this.currentBoardId);
  }

  // Event Listeners initialisieren
  initializeEventListeners() {
    // Board Management
  document.getElementById('createBoardBtn').addEventListener('click', () => {
    const payload = {
      title: "My Awesome Board",
      keywords: ["fun", "chat", "random"]
    };
    fetch('http://localhost:5000/set_super_peer', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    })
      .then(response => response.json())
      .then(data => console.log('Antwort von Python:', data))
      .catch(error => console.error('Fehler beim Aufruf von set_super_peer:', error));

    document.getElementById('createBoardModal').classList.remove('hidden');
  });


    document.getElementById('createBoardForm').addEventListener('submit', (e) => {
      e.preventDefault();
      this.createBoard();
    });

    document.getElementById('createBoardCancelBtn').addEventListener('click', () => {
      document.getElementById('createBoardModal').classList.add('hidden');
    });

    // Board Suche
    document.getElementById('boardSearchInput').addEventListener('input', (e) => {
      this.filterBoards(e.target.value);
    });

    // Karten Management (deine ursprünglichen Funktionen)
    this.setupModal();
    this.setupSearch();

    // Modal schließen beim Klick außerhalb
    document.addEventListener('click', (e) => {
      if (e.target.classList.contains('modal')) {
        e.target.classList.add('hidden');
      }
    });
  }

  // Board Management
  createBoard() {
    const name = document.getElementById('boardNameInput').value.trim();
    if (!name) return;

    const newBoard = {
      id: 'board-' + Date.now(),
      name: name,
      cards: [],
      useJsonFile: false // Neue Boards verwenden keine JSON-Datei
    };

    this.boards.push(newBoard);
    this.saveBoards();
    this.renderBoardTabs();
    this.switchToBoard(newBoard.id);

    document.getElementById('createBoardModal').classList.add('hidden');
    document.getElementById('boardNameInput').value = '';
  }

  deleteBoard(boardId) {
    if (this.boards.length <= 1) {
      alert('Sie müssen mindestens ein Board behalten!');
      return;
    }

    if (confirm('Sind Sie sicher, dass Sie dieses Board löschen möchten?')) {
      this.boards = this.boards.filter(board => board.id !== boardId);
      
      if (this.currentBoardId === boardId) {
        this.currentBoardId = this.boards[0].id;
        this.saveCurrentBoard();
      }
      
      this.saveBoards();
      this.renderBoardTabs();
      this.loadCurrentBoardCards();
    }
  }

  switchToBoard(boardId) {
    this.currentBoardId = boardId;
    this.saveCurrentBoard();
    this.renderBoardTabs();
    this.loadCurrentBoardCards();
    document.getElementById('searchInput').value = '';
  }

  renderBoardTabs() {
    const tabsContainer = document.getElementById('boardTabs');
    tabsContainer.innerHTML = '';

    this.boards.forEach(board => {
      const tab = document.createElement('button');
      tab.className = `board-tab ${board.id === this.currentBoardId ? 'active' : ''}`;
      tab.innerHTML = `
        ${this.escapeHtml(board.name)}
        <button class="delete-board" onclick="event.stopPropagation(); boardManager.deleteBoard('${board.id}')">&times;</button>
      `;
      tab.addEventListener('click', () => this.switchToBoard(board.id));
      tabsContainer.appendChild(tab);
    });
  }

  // Board-Filter Funktion
  filterBoards(searchTerm) {
    const tabsContainer = document.getElementById('boardTabs');
    const tabs = tabsContainer.querySelectorAll('.board-tab');
    
    if (!searchTerm.trim()) {
      // Alle Boards anzeigen
      tabs.forEach(tab => {
        tab.style.display = 'block';
      });
      return;
    }

    const query = searchTerm.toLowerCase();
    
    tabs.forEach((tab, index) => {
      const board = this.boards[index];
      const boardName = board.name.toLowerCase();
      
      // Board-Namen durchsuchen
      if (boardName.includes(query)) {
        tab.style.display = 'block';
      } else {
        tab.style.display = 'none';
      }
    });
  }

  // Karten für aktuelles Board laden (angepasst von deiner loadCards Funktion)
  async loadCurrentBoardCards() {
    const currentBoard = this.getCurrentBoard();
    if (!currentBoard) return;

    const board = document.getElementById('board');
    board.innerHTML = '';

    // Für "Sommer" Board: cards.json laden
    if (currentBoard.useJsonFile && currentBoard.cards.length === 0) {
      try {
        const response = await fetch('cards.json');
        if (response.ok) {
          const cardsFromJson = await response.json();
          // IDs hinzufügen falls nicht vorhanden
          cardsFromJson.forEach((card, index) => {
            if (!card.id) {
              card.id = `json-card-${index}`;
            }
          });
          currentBoard.cards = cardsFromJson;
          this.saveBoards();
        }
      } catch (error) {
        console.error('Fehler beim Laden der cards.json:', error);
      }
    }

    // Globale Variable für alle Karten des aktuellen Boards
    window.cardsData = currentBoard.cards;

    if (currentBoard.cards.length === 0) {
      board.innerHTML = `
        <div class="empty-state">
          <h3>Keine Karten vorhanden</h3>
          <p>Klicken Sie auf das + Symbol, um eine neue Karte hinzuzufügen.</p>
        </div>
      `;
      return;
    }

    currentBoard.cards.forEach(card => {
      this.addCardToBoard(card);
    });
  }

  // Karte zum Board hinzufügen (deine ursprüngliche Funktion, leicht angepasst)
  addCardToBoard(card) {
    const board = document.getElementById('board');
    const cardEl = document.createElement('article');
    cardEl.classList.add('card');
    cardEl.dataset.cardId = card.id; // Eindeutige ID für das DOM-Element

    cardEl.innerHTML = `
      <button class="edit-btn" title="Bearbeiten">&#9998;</button>
      <button class="delete-btn" title="Löschen">&times;</button>
      <h2>${this.escapeHtml(card.title)}</h2>
      <div class="author">von ${this.escapeHtml(card.author)}</div>
      <p class="content">${this.escapeHtml(card.content)}</p>
    `;

    // Edit-Button Funktion
    cardEl.querySelector('.edit-btn').addEventListener('click', () => {
      this.openEditModal(card, cardEl);
    });

    // Delete-Button Funktion
    cardEl.querySelector('.delete-btn').addEventListener('click', () => {
      this.deleteCard(card.id);
    });

    board.appendChild(cardEl);
  }

  // Karte löschen (neue separate Funktion)
  deleteCard(cardId) {
    // Karte aus DOM entfernen
    const cardEl = document.querySelector(`[data-card-id="${cardId}"]`);
    if (cardEl) {
      cardEl.remove();
    }

    // Karte aus aktuellem Board entfernen
    const currentBoard = this.getCurrentBoard();
    const index = currentBoard.cards.findIndex(c => c.id == cardId);
    if (index > -1) {
      currentBoard.cards.splice(index, 1);
      this.saveBoards();
    }

    // Auch aus globalem Array entfernen
    const globalIndex = window.cardsData.findIndex(c => c.id == cardId);
    if (globalIndex > -1) {
      window.cardsData.splice(globalIndex, 1);
    }
  }

  // Edit Modal öffnen (deine ursprüngliche Funktion, leicht angepasst)
  openEditModal(card, cardEl) {
    const editModal = document.getElementById('editModal');
    const editForm = document.getElementById('editCardForm');
    const editTitleInput = document.getElementById('editTitleInput');
    const editAuthorInput = document.getElementById('editAuthorInput');
    const editContentInput = document.getElementById('editContentInput');

    // Aktuelle Werte in das Formular laden
    editTitleInput.value = card.title;
    editAuthorInput.value = card.author;
    editContentInput.value = card.content;

    // Bearbeiten-Modal anzeigen
    editModal.classList.remove('hidden');

    // Event-Listener für das Formular
    const onSubmit = (e) => {
      e.preventDefault();

      // Werte aktualisieren
      card.title = editTitleInput.value.trim();
      card.author = editAuthorInput.value.trim();
      card.content = editContentInput.value.trim();

      // DOM aktualisieren
      cardEl.querySelector('h2').textContent = card.title;
      cardEl.querySelector('.author').textContent = `von ${card.author}`;
      cardEl.querySelector('.content').textContent = card.content;

      // Boards speichern
      this.saveBoards();

      // Bearbeiten-Modal schließen
      editModal.classList.add('hidden');

      // Event-Listener entfernen, um Duplikate zu vermeiden
      editForm.removeEventListener('submit', onSubmit);
    };

    editForm.addEventListener('submit', onSubmit);

    // Abbrechen-Button für Bearbeiten-Modal
    const cancelHandler = () => {
      editModal.classList.add('hidden');
      editForm.removeEventListener('submit', onSubmit);
      document.getElementById('editCancelBtn').removeEventListener('click', cancelHandler);
    };

    document.getElementById('editCancelBtn').addEventListener('click', cancelHandler);
  }

  // Modal Setup (deine ursprüngliche Funktion, angepasst)
  setupModal() {
    const addBtn = document.getElementById('addCardBtn');
    const addModal = document.getElementById('modal');
    const cancelBtn = document.getElementById('cancelBtn');
    const form = document.getElementById('cardForm');

    // Plus-Button öffnet Hinzufügen-Modal
    addBtn.addEventListener('click', () => {
      addModal.classList.remove('hidden');
    });

    // Abbrechen-Button schließt Hinzufügen-Modal und leert das Formular
    cancelBtn.addEventListener('click', () => {
      addModal.classList.add('hidden');
      form.reset();
    });

    // Formular absenden -> neue Karte hinzufügen
    form.addEventListener('submit', (e) => {
      e.preventDefault();

      const newCard = {
        id: Date.now(), // ID hinzufügen für eindeutige Identifikation
        title: document.getElementById('titleInput').value.trim(),
        author: document.getElementById('authorInput').value.trim(),
        content: document.getElementById('contentInput').value.trim(),
        timestamp: new Date().toISOString()
      };

      if (!newCard.title || !newCard.author || !newCard.content) {
        alert('Bitte alle Felder ausfüllen!');
        return;
      }

      fetch('http://localhost:5000/save_card', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(newCard)
      })
      .then(response => response.json())
      .then(data => console.log("Karte wurde serverseitig gespeichert:", data))
      .catch(error => console.error("Fehler beim Speichern der Karte:", error));


      // Karte zum DOM hinzufügen
      this.addCardToBoard(newCard);

      // Neu hinzugefügte Karte in aktuelles Board speichern
      const currentBoard = this.getCurrentBoard();
      currentBoard.cards.push(newCard);
      this.saveBoards();

      // Auch in globale Liste speichern
      window.cardsData.push(newCard);

      // Hinzufügen-Modal schließen und Formular zurücksetzen
      addModal.classList.add('hidden');
      form.reset();
    });
  }

  // Suche Setup - KORRIGIERT
  setupSearch() {
    const input = document.getElementById('searchInput');

    input.addEventListener('input', () => {
      const query = input.value.toLowerCase().trim();
      const board = document.getElementById('board');
      
      if (!window.cardsData || window.cardsData.length === 0) {
        board.innerHTML = `
          <div class="empty-state">
            <h3>Keine Karten vorhanden</h3>
            <p>Klicken Sie auf das + Symbol, um eine neue Karte hinzuzufügen.</p>
          </div>
        `;
        return;
      }

      // Alle Karten verstecken/zeigen statt DOM zu manipulieren
      const allCards = board.querySelectorAll('.card');
      let visibleCount = 0;

      if (!query) {
        // Alle Karten anzeigen
        allCards.forEach(cardEl => {
          cardEl.style.display = 'block';
          visibleCount++;
        });
      } else {
        // Karten nach Suchbegriff filtern
        allCards.forEach(cardEl => {
          const title = cardEl.querySelector('h2').textContent.toLowerCase();
          const author = cardEl.querySelector('.author').textContent.toLowerCase();
          const content = cardEl.querySelector('.content').textContent.toLowerCase();
          
          if (title.includes(query) || author.includes(query) || content.includes(query)) {
            cardEl.style.display = 'block';
            visibleCount++;
          } else {
            cardEl.style.display = 'none';
          }
        });
      }

      // Empty State nur anzeigen wenn keine Karten sichtbar sind
      const existingEmptyState = board.querySelector('.empty-state');
      if (visibleCount === 0 && query) {
        if (!existingEmptyState) {
          const emptyDiv = document.createElement('div');
          emptyDiv.className = 'empty-state';
          emptyDiv.innerHTML = `
            <h3>Keine Karten gefunden</h3>
            <p>Versuchen Sie einen anderen Suchbegriff.</p>
          `;
          board.appendChild(emptyDiv);
        }
      } else if (existingEmptyState) {
        existingEmptyState.remove();
      }
    });
  }

  // HTML escapen für Sicherheit
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}

// App initialisieren wenn DOM geladen ist
window.addEventListener('DOMContentLoaded', () => {
  window.boardManager = new BulletinBoardManager();
});