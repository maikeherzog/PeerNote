let peerInfo = {
  host: "127.0.0.1",  // fallback
  port: 8005          // fallback
};

fetch("http://localhost:5000/peer_info")
  .then(res => res.json())
  .then(data => {
    if (data.host && data.port) {
      peerInfo.host = data.host;
      peerInfo.port = data.port;
      console.log("Peer-Info geladen:", peerInfo);
    } else {
      console.warn("Peer-Info unvollständig, Fallback wird verwendet.");
    }
  })
  .catch(err => {
    console.error("Fehler beim Laden von /peer_info:", err);
  });


// Multi-Board Bulletin Board Manager
class BulletinBoardManager {
  constructor() {
    this.boards = this.loadBoards();
    this.remoteBoards = []; // Neue Eigenschaft für entfernte Boards
    this.currentBoardId = this.loadCurrentBoard();
    this.currentEditId = null;
    
    this.initializeEventListeners();
    this.loadRemoteBoards(); // Entfernte Boards laden
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

  // Erweiterte loadRemoteBoards() Funktion
  async loadRemoteBoards() {
    try {
      const response = await fetch("../data/received_boards.json");

      if (!response.ok) {
        throw new Error("Datei nicht gefunden oder ungültig");
      }

      const payload = await response.json();

      if (!Array.isArray(payload)) {
        console.warn("Keine gültigen Boards gefunden.");
        return;
      }

      console.log("[REMOTE BOARDS]:", payload);

      // Entfernte Boards in remoteBoards Array speichern
      this.remoteBoards = payload.map(board => ({
        id: `remote-${board.board_id}`,
        name: board.board_title,
        cards: [],
        isRemote: true,
        remoteData: board // Alle Original-Daten speichern
      }));

      // Board-Tabs neu rendern (inkl. entfernte Boards)
      this.renderBoardTabs();

    } catch (error) {
      console.warn("received_boards.json konnte nicht geladen werden:", error);
    }
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

  // Erweiterte getCurrentBoard() Funktion
  getCurrentBoard() {
    // Erst in lokalen Boards suchen
    let board = this.boards.find(board => board.id === this.currentBoardId);
    
    // Falls nicht gefunden, in entfernten Boards suchen
    if (!board) {
      board = this.remoteBoards.find(board => board.id === this.currentBoardId);
    }
    
    return board;
  }

  // Event Listeners initialisieren
  initializeEventListeners() {
    // Board Management - Second Approach: Create local board first
    document.getElementById('createBoardBtn').addEventListener('click', () => {
      document.getElementById('createBoardModal').classList.remove('hidden');
    });

    document.getElementById('createBoardForm').addEventListener('submit', (e) => {
      e.preventDefault();
      
      const boardName = document.getElementById('boardNameInput').value.trim();
      if (!boardName) {
        alert('Bitte geben Sie einen Board-Namen ein!');
        return;
      }
      
      // Create the board locally FIRST
      this.createBoard();
      
      // THEN register with bootstrap
      const payload = {
        title: boardName,
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
      .then(data => {
        console.log('Bootstrap registration:', data);
      })
      .catch(error => {
        console.error('Bootstrap registration failed:', error);
      });
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
    // Verhindern, dass entfernte Boards gelöscht werden
    if (boardId.startsWith('remote-')) {
      alert('Entfernte Boards können nicht gelöscht werden!');
      return;
    }

    if (this.boards.length <= 1) {
      alert('Sie müssen mindestens ein Board behalten!');
      return;
    }

    if (confirm('Sind Sie sicher, dass Sie dieses Board löschen möchten?')) {
      // Get the board before deleting it
      const boardToDelete = this.boards.find(board => board.id === boardId);
      
      // Send unregistration request to bootstrap
      if (boardToDelete && boardToDelete.name !== 'Sommer') { // Don't unregister default board
        fetch('http://localhost:5000/unregister_board', {
          method: 'DELETE',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            board_title: boardToDelete.name
          })
        })
        .then(response => response.json())
        .then(data => console.log("Board unregistered from bootstrap:", data))
        .catch(error => console.error("Error unregistering board:", error));
      }
      
      // Continue with local deletion
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

  // Erweiterte renderBoardTabs() Funktion
  renderBoardTabs() {
    const tabsContainer = document.getElementById('boardTabs');
    tabsContainer.innerHTML = '';

    // Alle Boards kombinieren (lokale + entfernte)
    const allBoards = [...this.boards, ...this.remoteBoards];

    allBoards.forEach(board => {
      const tab = document.createElement('button');
      tab.className = `board-tab ${board.id === this.currentBoardId ? 'active' : ''}`;
      
      // Unterschiedliche Darstellung für entfernte Boards
      if (board.isRemote) {
        tab.innerHTML = `
          <span class="remote-indicator">🌐</span>
          ${this.escapeHtml(board.name)}
          <span class="remote-info">(${board.remoteData.peer_host}:${board.remoteData.peer_port})</span>
        `;
        tab.classList.add('remote-board-tab');
      } else {
        tab.innerHTML = `
          ${this.escapeHtml(board.name)}
          <button class="delete-board" onclick="event.stopPropagation(); boardManager.deleteBoard('${board.id}')">&times;</button>
        `;
      }
      
      tab.addEventListener('click', () => this.switchToBoard(board.id));
      tabsContainer.appendChild(tab);
    });
  }

  // Erweiterte Board-Filter Funktion
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
    const allBoards = [...this.boards, ...this.remoteBoards];
    
    tabs.forEach((tab, index) => {
      const board = allBoards[index];
      const boardName = board.name.toLowerCase();
      
      // Board-Namen durchsuchen
      if (boardName.includes(query)) {
        tab.style.display = 'block';
      } else {
        tab.style.display = 'none';
      }
    });
  }

  // Erweiterte loadCurrentBoardCards() Funktion
  async loadCurrentBoardCards() {
    const currentBoard = this.getCurrentBoard();
    if (!currentBoard) return;

    const board = document.getElementById('board');
    board.innerHTML = '';

    // Spezielle Behandlung für entfernte Boards
    if (currentBoard.isRemote) {
      board.innerHTML = `
        <div class="empty-state">
          <h3>Keine Karten vorhanden</h3>
          <p>Klicken Sie auf das + Symbol, um eine neue Karte hinzuzufügen.</p>
        </div>
      `;
      
      // Hier könnten Sie später die Karten vom entfernten Peer laden
      // z.B. fetch(`http://${currentBoard.remoteData.peer_host}:${currentBoard.remoteData.peer_port}/cards`)
      
      return;
    }

    // Rest der ursprünglichen Logik für lokale Boards...
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

      fetch(`http://localhost:5000/delete_card/${card.id}`, {
        method: 'DELETE'
      })
      .then(response => response.json())
      .then(data => console.log("Karte serverseitig gelöscht:", data))
      .catch(error => console.error("Fehler beim Löschen der Karte:", error));
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
      card.timestamp = new Date().toISOString(); 

      // DOM aktualisieren
      cardEl.querySelector('h2').textContent = card.title;
      cardEl.querySelector('.author').textContent = `von ${card.author}`;
      cardEl.querySelector('.content').textContent = card.content;

      // Boards speichern
      this.saveBoards();

      fetch('http://localhost:5000/update_card', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(card)
      })
      .then(response => response.json())
      .then(data => {
        console.log("Karte serverseitig aktualisiert:", data);
      })
      .catch(error => {
        console.error("Fehler beim Aktualisieren der Karte:", error);
      });

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
      // Verhindern, dass Karten zu entfernten Boards hinzugefügt werden
      const currentBoard = this.getCurrentBoard();
      if (currentBoard && currentBoard.isRemote) {
        alert('Sie können keine Karten zu entfernten Boards hinzufügen!');
        return;
      }
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
        id: self.crypto.randomUUID(),
        title: document.getElementById('titleInput').value.trim(),
        author: document.getElementById('authorInput').value.trim(),
        content: document.getElementById('contentInput').value.trim(),
        timestamp: new Date().toISOString(),
        comments: {},
        votes: 0,
        host: peerInfo.host,
        port: peerInfo.port
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