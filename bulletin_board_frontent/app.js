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
    <h2>${card.title}</h2>
    <div class="author">von ${card.author}</div>
    <p class="content">${card.content}</p>
  `;

  board.appendChild(cardEl);
}

// Setup für das Modal mit Button-Events
function setupModal() {
  const addBtn = document.getElementById('addCardBtn');
  const modal = document.getElementById('modal');
  const cancelBtn = document.getElementById('cancelBtn');
  const form = document.getElementById('cardForm');

  // Plus-Button öffnet Modal
  addBtn.addEventListener('click', () => {
    modal.classList.remove('hidden');
  });

  // Abbrechen-Button schließt Modal und leert das Formular
  cancelBtn.addEventListener('click', () => {
    modal.classList.add('hidden');
    form.reset();
  });

  // Formular absenden -> neue Karte hinzufügen
  form.addEventListener('submit', e => {
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

    // Modal schließen und Formular zurücksetzen
    modal.classList.add('hidden');
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
