RobRunObsOverlay

Un overlay OBS qui affiche en direct les stats de ton wipe ROB RUN : parties, % de survie, morts, KO, objet en main, ping et chrono de la partie en cours.

Il tourne sur ton PC, affiche le résultat dans une source Navigateur d'OBS. Rien à installer à part l'exe.

Outil non officiel, sans lien avec Kefir ni ROB RUN. Il ne touche pas à la mémoire du jeu et n'injecte rien.

Ce que l'overlay affiche
Élément	Description
Wipe · jour X	Le numéro du jour depuis le début du wipe
% de survie	Parties terminées en vie sur le total de parties terminées
Parties	Nombre de parties jouées en tant que robber
Morts	Morts pendant une partie
KO	Mises à terre pendant une partie, puis réanimé
Objet en main	L'arme ou l'objet que tu tiens
Ping	Ton ping vers le serveur de jeu
Chrono	« Partie en cours 3:12 » pendant un run, puis « Dernière partie 6:57 »
Comment les parties sont comptées
Une partie commence quand tu deviens robber à Looty Bay, et se termine quand tu quittes la map.
Elle est perdue si tu es mort pendant, sinon réussie (sortie en vie).
Les morts et KO ne comptent que pendant une partie : mourir dans une colonie ou un centre de vente n'est pas compté.
Un KO suivi d'une mort sans réanimation compte uniquement comme une mort.
Les stats se cumulent entre les sessions de jeu, tu n'as rien à faire.
Installation
Télécharge RobRunObsOverlay.exe depuis la dernière release.
Lance-le et laisse la fenêtre ouverte (tu peux la réduire).
Au premier lancement, une page Twitch s'ouvre : clique sur Autoriser (voir Accès réservé).
Dans OBS : Sources → + → Navigateur, colle l'adresse http://localhost:47821/ (elle est déjà copiée dans ton presse-papiers), largeur 340, hauteur 360.

Si le port 47821 est déjà pris, l'app prend le suivant (47822...). Utilise toujours l'adresse affichée dans la fenêtre.

Lance l'app avant de devenir robber : si elle démarre en pleine partie, cette partie n'est pas détectée.

Dans la fenêtre : 3 touches
Touche	Action
R	Nouveau wipe : remet toutes les stats à zéro (avec confirmation O/N)
O	Rouvre la page de l'overlay dans le navigateur
A	Active ou désactive le démarrage automatique avec Windows (l'état actuel est affiché)
Fonctionnalités
Démarrage automatique avec Windows, sans ouvrir de fenêtre de navigateur. Désactivable avec la touche A.
Mise à jour automatique : à chaque lancement, l'app vérifie s'il existe une version plus récente et se met à jour toute seule. Tes stats sont conservées.
Aucune installation : un simple .exe, pas besoin de Python.
Données locales : tes stats restent sur ton PC.
Accès réservé

L'outil est réservé aux abonnés de la chaîne Twitch zertook et à ses modérateurs.

Au premier lancement, une page Twitch s'ouvre : clique sur Autoriser. C'est la seule manipulation.
Aux lancements suivants, la vérification se fait toute seule, en quelques secondes.
L'app peut seulement lire si tu es abonné ou modérateur de la chaîne. Elle n'a accès à rien d'autre sur ton compte.
Sans connexion internet, l'app démarre quand même si ta dernière vérification date de moins de 3 jours.
Si l'app reste inutilisée plus de 30 jours, Twitch demande de cliquer à nouveau sur Autoriser.
Ce qui n'est pas suivi

Le jeu n'écrit pas ces informations dans son fichier log, l'overlay ne peut donc pas les afficher :

les kills
les arrestations
les montants d'argent et le butin
les événements de clan (revendications, attaques)
Limites connues
Une partie interrompue (crash du jeu, déconnexion) est comptée comme réussie.
Windows uniquement.
Certains antivirus peuvent signaler à tort l'exe (courant pour les programmes Python empaquetés). Si ça arrive, ajoute-le aux exceptions.
Où sont mes données ?

Tout est dans %LOCALAPPDATA%\RobRunObsOverlay (ouvre-le avec Win + R) :

stats_state.json : tes compteurs
twitch_auth.json : ta connexion Twitch mémorisée

Le jeu écrit son log dans %USERPROFILE%\AppData\LocalLow\Kefir\ROB RUN\Player.log.

Désinstaller
Dans la fenêtre, appuie sur A pour retirer le démarrage automatique (ou lance RobRunObsOverlay.exe --no-autostart).
Ferme l'app et supprime l'exe.
Supprime le dossier %LOCALAPPDATA%\RobRunObsOverlay si tu veux effacer tes stats.
Options en ligne de commande
Option	Effet
--no-browser	N'ouvre pas la page au lancement
--autostart / --no-autostart	Active / désactive le démarrage avec Windows
--no-update	Ne cherche pas de mise à jour
--port 47821	Choisit le port de départ
Contact

Un souci, une idée ? Discord : [zertok](https://discord.gg/Qn9Bb4Ejsc)
