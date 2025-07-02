// Karten aus der JSON-Datei laden und anzeigen
async function loadCards() {
  try {
    const response = await fetch('cards.json');
    if (!response.ok) throw new Error('Konnte cards.json nicht laden');
    const cards = await response.json();
    const board = document.getElementById('board');

    // Globale Variable für alle Karten (inkl. neu hinzugefügte)
    window.cardsData = cards;

    cards.forEach(card => {
      addCardToBoard(card);
    });
  } catch (error) {
    console.error('Fehler beim Laden der Karten:', error);
  }
}

// Funktion, um eine Karte als HTML-Element ins Board einzufügen
function addCardToBoard(card) {
  const board = document.getElementById('board');
  const cardEl = document.createElement('article');
  cardEl.classList.add('card');

  cardEl.innerHTML = `
    <button class="edit-btn" title="Bearbeiten">&#9998;</button>
    <button class="delete-btn" title="Löschen">&times;</button>
    <h2>${card.title}</h2>
    <div class="author">von ${card.author}</div>
    <p class="content">${card.content}</p>
  `;

  // Edit-Button Funktion
  cardEl.querySelector('.edit-btn').addEventListener('click', () => {
    openEditModal(card, cardEl);
  });

  // Delete-Button Funktion
  cardEl.querySelector('.delete-btn').addEventListener('click', () => {
    board.removeChild(cardEl);

    // Optional: Karte auch aus globalem Array entfernen
    const index = window.cardsData.indexOf(card);
    if (index > -1) {
      window.cardsData.splice(index, 1);
    }
  });

  board.appendChild(cardEl);
}

// Funktion, um das Bearbeiten-Modal zu öffnen
function openEditModal(card, cardEl) {
  const editModal = document.getElementById('editModal'); // Bearbeiten-Modal
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

    // Bearbeiten-Modal schließen
    editModal.classList.add('hidden');

    // Event-Listener entfernen, um Duplikate zu vermeiden
    editForm.removeEventListener('submit', onSubmit);
  };

  editForm.addEventListener('submit', onSubmit);

  // Abbrechen-Button für Bearbeiten-Modal
  document.getElementById('editCancelBtn').addEventListener('click', () => {
    editModal.classList.add('hidden');
    editForm.removeEventListener('submit', onSubmit);
  });
}

function setupModal() {
  const addBtn = document.getElementById('addCardBtn');
  const addModal = document.getElementById('modal'); // Hinzufügen-Modal
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
      title: document.getElementById('titleInput').value.trim(),
      author: document.getElementById('authorInput').value.trim(),
      content: document.getElementById('contentInput').value.trim(),
    };

    if (!newCard.title || !newCard.author || !newCard.content) {
      alert('Bitte alle Felder ausfüllen!');
      return;
    }

    addCardToBoard(newCard);

    // Neu hinzugefügte Karte auch in globale Liste speichern
    window.cardsData.push(newCard);

    // Hinzufügen-Modal schließen und Formular zurücksetzen
    addModal.classList.add('hidden');
    form.reset();
  });
}

function setupSearch() {
  const input = document.getElementById('searchInput');
  const board = document.getElementById('board');

  input.addEventListener('input', () => {
    const query = input.value.toLowerCase();

    // Vorhandene Karten aus globalem Array filtern
    const filtered = window.cardsData.filter(card => {
      return (
        card.title.toLowerCase().includes(query) ||
        card.author.toLowerCase().includes(query) ||
        card.content.toLowerCase().includes(query)
      );
    });

    // Board leeren und gefilterte Karten neu einfügen
    board.innerHTML = '';
    filtered.forEach(addCardToBoard);
  });
}


// Wenn DOM geladen ist, Karten laden und Modal initialisieren
window.addEventListener('DOMContentLoaded', () => {
  loadCards();
  setupModal();
  setupSearch();
});
