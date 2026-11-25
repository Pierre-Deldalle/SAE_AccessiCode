"""
Explications par critère RGAA 4.1.2, destinées à l'utilisateur final.

Pour chaque critère : son intitulé officiel, ce qu'un défaut change concrètement
pour les personnes concernées (sans jargon), et le lien vers sa fiche officielle.
Les tests RGAA disent ce qui ne va pas ; cette table dit pourquoi cela gêne.

Pour ajouter un critère : ajouter une entrée dans ``CRITERIA``, avec l'intitulé
recopié depuis la méthode officielle.
"""

from __future__ import annotations

from dataclasses import dataclass

RGAA_METHOD_URL = "https://accessibilite.numerique.gouv.fr/methode/criteres-et-tests/"


@dataclass(frozen=True)
class CriterionInfo:
    """Intitulé, impact pour les utilisateurs et fiche officielle d'un critère."""

    criterion_id: str
    title: str
    impact: str

    @property
    def url(self) -> str:
        return f"{RGAA_METHOD_URL}#{self.criterion_id}"


_ENTRIES = (
    # ---- Thème 2 : cadres ----
    CriterionInfo(
        "2.1",
        "Chaque cadre a-t-il un titre de cadre ?",
        "Une personne aveugle qui utilise un lecteur d'écran entend seulement « cadre » : sans titre, elle ne "
        "sait pas ce que contient ce bloc (carte, vidéo, formulaire…) avant d'y entrer et de l'explorer.",
    ),
    CriterionInfo(
        "2.2",
        "Pour chaque cadre ayant un titre de cadre, ce titre de cadre est-il pertinent ?",
        "Un titre vague comme « iframe » ou « cadre 1 » n'aide pas une personne qui utilise un lecteur d'écran : "
        "elle doit ouvrir le cadre pour découvrir son contenu, et ne peut pas choisir rapidement où aller.",
    ),
    # ---- Thème 3 : couleurs ----
    CriterionInfo(
        "3.1",
        "Dans chaque page web, l'information ne doit pas être donnée uniquement par la couleur. Cette règle est-elle "
        "respectée ?",
        "Une personne daltonienne ou malvoyante ne distingue pas toujours les couleurs : si seule la couleur signale "
        "une information (un champ en erreur en rouge, un statut en vert), elle passe à côté. Une personne aveugle "
        "non plus, car le lecteur d'écran n'annonce pas les couleurs.",
    ),
    CriterionInfo(
        "3.2",
        "Dans chaque page web, le contraste entre la couleur du texte et la couleur de son arrière-plan est-il "
        "suffisamment élevé (hors cas particuliers) ?",
        "Un texte gris clair sur fond blanc est difficile, voire impossible, à lire pour une personne malvoyante, une "
        "personne âgée ou quelqu'un qui consulte son téléphone en plein soleil.",
    ),
    CriterionInfo(
        "3.3",
        "Dans chaque page web, les couleurs utilisées dans les composants d'interface ou les éléments graphiques "
        "porteurs d'informations sont-elles suffisamment contrastées (hors cas particuliers) ?",
        "Un bouton, le contour d'un champ ou un graphique trop pâle par rapport au fond passe inaperçu pour une "
        "personne malvoyante : elle ne voit pas où cliquer, où écrire, ni ce que montre le graphique.",
    ),
    # ---- Thème 4 : multimédia ----
    CriterionInfo(
        "4.1",
        "Chaque média temporel pré-enregistré a-t-il, si nécessaire, une transcription textuelle "
        "ou une audiodescription (hors cas particuliers) ?",
        "Une personne sourde ou malentendante n'entend pas un enregistrement audio, et une personne aveugle "
        "ne voit pas une vidéo. Sans version écrite ni description sonore, elles n'ont pas accès à l'information.",
    ),
    CriterionInfo(
        "4.2",
        "Pour chaque média temporel pré-enregistré ayant une transcription textuelle ou une audiodescription "
        "synchronisée, celles-ci sont-elles pertinentes (hors cas particuliers) ?",
        "Les personnes sourdes, malentendantes ou aveugles comptent sur la version écrite ou la description sonore "
        "pour comprendre le média. Si elle est incomplète ou inexacte, elles passent à côté d'une partie du contenu.",
    ),
    CriterionInfo(
        "4.3",
        "Chaque média temporel synchronisé pré-enregistré a-t-il, si nécessaire, des sous-titres synchronisés "
        "(hors cas particuliers) ?",
        "Sans sous-titres, une personne sourde ou malentendante ne peut pas suivre les dialogues "
        "ni les bruits importants d'une vidéo.",
    ),
    CriterionInfo(
        "4.4",
        "Pour chaque média temporel synchronisé pré-enregistré ayant des sous-titres synchronisés, "
        "ces sous-titres sont-ils pertinents ?",
        "Des sous-titres incomplets, erronés ou décalés par rapport à l'image font perdre le fil aux personnes "
        "sourdes ou malentendantes, qui ne peuvent pas s'aider du son pour corriger.",
    ),
    CriterionInfo(
        "4.5",
        "Chaque média temporel pré-enregistré a-t-il, si nécessaire, une audiodescription synchronisée "
        "(hors cas particuliers) ?",
        "Une personne aveugle ou malvoyante entend la vidéo mais ne voit pas ce qui se passe à l'écran. "
        "Sans une voix qui décrit les scènes importantes, elle manque une partie de l'histoire ou de l'information.",
    ),
    CriterionInfo(
        "4.6",
        "Pour chaque média temporel pré-enregistré ayant une audiodescription synchronisée, "
        "celle-ci est-elle pertinente ?",
        "Si la description sonore oublie des actions ou des textes affichés à l'écran, les personnes aveugles "
        "ou malvoyantes restent privées de ces informations visuelles.",
    ),
    CriterionInfo(
        "4.7",
        "Chaque média temporel est-il clairement identifiable (hors cas particuliers) ?",
        "Une personne aveugle qui se fait lire la page par un lecteur d'écran ne voit pas l'image d'aperçu. "
        "Sans titre ou texte qui présente le média, elle ne sait pas ce qu'elle va écouter ou regarder.",
    ),
    CriterionInfo(
        "4.8",
        "Chaque média non temporel a-t-il, si nécessaire, une alternative (hors cas particuliers) ?",
        "Une carte interactive ou une animation peut être impossible à percevoir ou à manipuler pour une personne "
        "aveugle ou qui n'utilise pas de souris. Sans version de remplacement, elle n'accède pas à son contenu.",
    ),
    CriterionInfo(
        "4.9",
        "Pour chaque média non temporel ayant une alternative, cette alternative est-elle pertinente ?",
        "Si la version de remplacement ne donne pas les mêmes informations ou ne permet pas les mêmes actions, "
        "les personnes qui en dépendent restent privées d'une partie du contenu.",
    ),
    CriterionInfo(
        "4.10",
        "Chaque son déclenché automatiquement est-il contrôlable par l’utilisateur ?",
        "Un son qui démarre tout seul couvre la voix du lecteur d'écran : une personne aveugle n'entend plus "
        "sa page et peine à trouver comment l'arrêter. Il gêne aussi les personnes qui ont du mal à se concentrer.",
    ),
    CriterionInfo(
        "4.11",
        "La consultation de chaque média temporel est-elle, si nécessaire, contrôlable par le clavier "
        "et tout dispositif de pointage ?",
        "Les personnes qui naviguent au clavier, sans souris, ou avec un écran tactile doivent pouvoir lancer, "
        "mettre en pause et arrêter une vidéo ou régler le son. Sinon, elles ne peuvent ni la regarder ni la couper.",
    ),
    CriterionInfo(
        "4.12",
        "La consultation de chaque média non temporel est-elle contrôlable par le clavier "
        "et tout dispositif de pointage ?",
        "Si une carte interactive ou une animation ne se commande qu'à la souris, les personnes qui naviguent "
        "au clavier, par exemple à cause d'un handicap moteur, ne peuvent pas s'en servir.",
    ),
    CriterionInfo(
        "4.13",
        "Chaque média temporel et non temporel est-il compatible avec les technologies d’assistance "
        "(hors cas particuliers) ?",
        "Les personnes aveugles utilisent un lecteur d'écran qui lit la page à voix haute. Si le lecteur vidéo "
        "ou le média ne lui donne pas le nom de ses boutons et de son contenu, elles ne peuvent ni le comprendre "
        "ni le commander.",
    ),
    # ---- Thème 5 : tableaux ----
    CriterionInfo(
        "5.1",
        "Chaque tableau de données complexe a-t-il un résumé ?",
        "Une personne aveugle découvre un tableau case par case avec son lecteur d'écran, sans vue d'ensemble. "
        "Si un tableau à plusieurs niveaux d'en-têtes n'est pas présenté, elle a du mal à comprendre comment le lire.",
    ),
    CriterionInfo(
        "5.2",
        "Pour chaque tableau de données complexe ayant un résumé, celui-ci est-il pertinent ?",
        "Un résumé qui n'explique pas comment le tableau est organisé ne sert à rien à une personne aveugle : "
        "elle doit parcourir toutes les cases pour deviner le sens de lecture.",
    ),
    CriterionInfo(
        "5.3",
        "Pour chaque tableau de mise en forme, le contenu linéarisé reste-t-il compréhensible ?",
        "Un lecteur d'écran lit les cases d'un tableau l'une après l'autre, ligne par ligne. Si un tableau sert "
        "seulement à disposer la page, les textes peuvent alors être lus dans le désordre et perdre leur sens.",
    ),
    CriterionInfo(
        "5.4",
        "Pour chaque tableau de données ayant un titre, le titre est-il correctement associé au tableau de données ?",
        "Une personne aveugle peut passer d'un tableau à l'autre en entendant leur titre. Si le titre n'est pas "
        "relié au tableau, elle ne sait pas ce que contient le tableau avant de l'avoir parcouru.",
    ),
    CriterionInfo(
        "5.5",
        "Pour chaque tableau de données ayant un titre, celui-ci est-il pertinent ?",
        "Un titre vague comme « Tableau » ou « Données » n'aide pas une personne qui utilise un lecteur d'écran "
        "à savoir de quoi parle le tableau ni à choisir celui qu'elle cherche.",
    ),
    CriterionInfo(
        "5.6",
        "Pour chaque tableau de données, chaque en-tête de colonne et chaque en-tête de ligne "
        "sont-ils correctement déclarés ?",
        "Le lecteur d'écran annonce le nom de la colonne ou de la ligne avant chaque valeur. Si les en-têtes "
        "ne sont pas reconnus comme tels, une personne aveugle entend des chiffres sans savoir à quoi ils "
        "correspondent.",
    ),
    CriterionInfo(
        "5.7",
        "Pour chaque tableau de données, la technique appropriée permettant d’associer chaque cellule "
        "avec ses en-têtes est-elle utilisée (hors cas particuliers) ?",
        "Dans un tableau, une personne aveugle a besoin d'entendre à quelle ligne et à quelle colonne "
        "appartient chaque case. Si ce lien est absent ou faux, elle ne peut pas interpréter les valeurs, "
        "ou les interprète mal.",
    ),
    CriterionInfo(
        "5.8",
        "Chaque tableau de mise en forme ne doit pas utiliser d’éléments propres aux tableaux de données. "
        "Cette règle est-elle respectée ?",
        "Un tableau qui sert seulement à disposer la page, mais qui contient un titre ou des en-têtes, est "
        "présenté par le lecteur d'écran comme un vrai tableau de données : une personne aveugle cherche alors "
        "des lignes et des colonnes qui n'ont pas de sens.",
    ),
    # ---- Thème 7 : scripts ----
    CriterionInfo(
        "7.1",
        "Chaque script est-il, si nécessaire, compatible avec les technologies d'assistance ?",
        "Un bouton ou un menu fabriqué par le code de la page, sans les bonnes informations, est lu comme un simple "
        "texte par le lecteur d'écran : une personne aveugle ne sait pas qu'elle peut l'activer, ni s'il est "
        "ouvert, fermé ou coché.",
    ),
    CriterionInfo(
        "7.2",
        "Pour chaque script ayant une alternative, cette alternative est-elle pertinente ?",
        "Quand le code de la page ne peut pas s'exécuter (navigateur ancien, réglage de sécurité), la version de "
        "remplacement doit offrir la même chose : un simple « Activez JavaScript » laisse la personne sans accès "
        "au contenu ou au service.",
    ),
    CriterionInfo(
        "7.3",
        "Chaque script est-il contrôlable par le clavier et par tout dispositif de pointage (hors cas particuliers) ?",
        "Les personnes qui ne peuvent pas utiliser de souris (handicap moteur, personnes aveugles) naviguent au "
        "clavier : un menu ou un bouton qui ne réagit qu'au clic de la souris leur est inutilisable.",
    ),
    CriterionInfo(
        "7.4",
        "Pour chaque script qui initie un changement de contexte, l'utilisateur est-il averti ou en a-t-il le "
        "contrôle ?",
        "Quand la page change toute seule (nouvelle page, formulaire envoyé dès qu'on choisit dans une liste), une "
        "personne qui utilise un lecteur d'écran ou qui a des difficultés d'attention perd ses repères sans "
        "comprendre ce qui s'est passé.",
    ),
    CriterionInfo(
        "7.5",
        "Dans chaque page web, les messages de statut sont-ils correctement restitués par les technologies "
        "d'assistance ?",
        "Un message qui apparaît sans recharger la page (« Message envoyé », « Erreur dans le formulaire ») n'est "
        "pas lu par le lecteur d'écran s'il n'est pas signalé : une personne aveugle ne sait pas si son action "
        "a réussi.",
    ),
    # ---- Thème 9 : structuration de l'information ----
    CriterionInfo(
        "9.1",
        "Dans chaque page web, l’information est-elle structurée par l’utilisation appropriée de titres ?",
        "Beaucoup de personnes aveugles parcourent une page en sautant de titre en titre avec leur lecteur d'écran, "
        "comme on lit un sommaire. Si les titres manquent, sont vides ou mal ordonnés, elles ne trouvent pas les "
        "parties de la page et comprennent mal son organisation.",
    ),
    CriterionInfo(
        "9.2",
        "Dans chaque page web, la structure du document est-elle cohérente (hors cas particuliers) ?",
        "Une personne qui utilise un lecteur d'écran peut aller directement au menu, au contenu principal ou au bas "
        "de page, à condition que ces zones soient signalées comme telles. Sinon, elle doit écouter la page depuis "
        "le début pour trouver ce qu'elle cherche.",
    ),
    CriterionInfo(
        "9.3",
        "Dans chaque page web, chaque liste est-elle correctement structurée ?",
        "Pour une vraie liste, le lecteur d'écran annonce « liste de 5 éléments » puis chaque élément. Si la liste "
        "est seulement dessinée avec des tirets ou des numéros, une personne aveugle ne sait ni où elle commence, "
        "ni où elle finit, ni combien d'éléments elle contient.",
    ),
    CriterionInfo(
        "9.4",
        "Dans chaque page web, chaque citation est-elle correctement indiquée ?",
        "Une personne qui utilise un lecteur d'écran ne voit pas les guillemets, l'italique ou le retrait qui "
        "signalent une citation. Si elle n'est pas indiquée comme telle, elle peut prendre les paroles d'une autre "
        "personne pour celles de l'auteur de la page.",
    ),
    # ---- Thème 11 : formulaires ----
    CriterionInfo(
        "11.1",
        "Chaque champ de formulaire a-t-il une étiquette ?",
        "Une personne aveugle qui utilise un lecteur d'écran entend seulement « zone de saisie » : sans étiquette, "
        "elle ne sait pas s'il faut y écrire son nom, son adresse ou son numéro de téléphone.",
    ),
    CriterionInfo(
        "11.2",
        "Chaque étiquette associée à un champ de formulaire est-elle pertinente (hors cas particuliers) ?",
        "Une étiquette vague comme « Champ 1 » ou « Saisir » ne dit pas ce qu'il faut écrire : une personne qui "
        "utilise un lecteur d'écran, ou qui a des difficultés de compréhension, risque de se tromper. Une personne "
        "qui commande l'ordinateur à la voix doit aussi pouvoir dire le mot affiché pour atteindre le champ.",
    ),
    CriterionInfo(
        "11.3",
        "Dans chaque formulaire, chaque étiquette associée à un champ de formulaire ayant la même fonction et "
        "répétée plusieurs fois dans une même page ou dans un ensemble de pages est-elle cohérente ?",
        "Si la même information s'appelle « Courriel » à un endroit et « Adresse électronique » ailleurs, une "
        "personne qui a des difficultés de compréhension ou de mémoire peut croire qu'on lui demande deux choses "
        "différentes.",
    ),
    CriterionInfo(
        "11.4",
        "Dans chaque formulaire, chaque étiquette de champ et son champ associé sont-ils accolés (hors cas "
        "particuliers) ?",
        "Une personne malvoyante qui agrandit fortement l'écran ne voit qu'une petite partie de la page à la fois : "
        "si l'étiquette est loin de son champ, elle ne sait plus quel texte correspond à quelle zone de saisie.",
    ),
    CriterionInfo(
        "11.5",
        "Dans chaque formulaire, les champs de même nature sont-ils regroupés, si nécessaire ?",
        "Sans regroupement, une personne qui utilise un lecteur d'écran entend « Oui », « Non » ou « Jour », "
        "« Mois », « Année » sans savoir à quelle question ces champs se rapportent.",
    ),
    CriterionInfo(
        "11.6",
        "Dans chaque formulaire, chaque regroupement de champs de même nature a-t-il une légende ?",
        "Un groupe de champs sans titre ne dit pas à quoi il sert : une personne qui utilise un lecteur d'écran "
        "entend les choix proposés (« Madame », « Monsieur ») sans entendre la question posée.",
    ),
    CriterionInfo(
        "11.7",
        "Dans chaque formulaire, chaque légende associée à un regroupement de champs de même nature est-elle "
        "pertinente ?",
        "Un titre de groupe vague comme « Informations » ou « Choix » n'aide pas : une personne qui utilise un "
        "lecteur d'écran ne sait toujours pas ce que ce groupe de champs lui demande.",
    ),
    CriterionInfo(
        "11.8",
        "Dans chaque formulaire, les items de même nature d'une liste de choix sont-ils regroupés de manière "
        "pertinente ?",
        "Dans une longue liste déroulante sans catégories, une personne qui utilise un lecteur d'écran doit écouter "
        "les options une par une, sans repère pour trouver rapidement la bonne.",
    ),
    CriterionInfo(
        "11.9",
        "Dans chaque formulaire, l'intitulé de chaque bouton est-il pertinent (hors cas particuliers) ?",
        "Un bouton sans texte, ou intitulé « OK », ne dit pas ce qu'il va faire : une personne qui utilise un "
        "lecteur d'écran ne sait pas s'il envoie, efface ou annule le formulaire, et une personne qui commande "
        "l'ordinateur à la voix ne peut l'activer que si son nom reprend le texte affiché.",
    ),
    CriterionInfo(
        "11.10",
        "Dans chaque formulaire, le contrôle de saisie est-il utilisé de manière pertinente (hors cas particuliers) ?",
        "Si les champs obligatoires ne sont pas signalés, ou si un message d'erreur n'indique pas quel champ "
        "corriger, une personne aveugle ou qui a des difficultés de compréhension ne peut pas savoir ce qui "
        "empêche l'envoi du formulaire.",
    ),
    CriterionInfo(
        "11.11",
        "Dans chaque formulaire, le contrôle de saisie est-il accompagné, si nécessaire, de suggestions facilitant "
        "la correction des erreurs de saisie ?",
        "Un message comme « Saisie incorrecte », sans exemple ni format attendu, oblige à deviner : une personne qui "
        "a des difficultés de lecture ou de compréhension peut rester bloquée sans pouvoir terminer sa démarche.",
    ),
    CriterionInfo(
        "11.12",
        "Pour chaque formulaire qui modifie ou supprime des données, ou qui transmet des réponses à un test ou à un "
        "examen, ou dont la validation a des conséquences financières ou juridiques, les données saisies "
        "peuvent-elles être modifiées, mises à jour ou récupérées par l'utilisateur ?",
        "Une personne qui fait plus facilement des erreurs de saisie (tremblements, vue réduite, troubles de "
        "l'attention) doit pouvoir vérifier, corriger ou annuler avant qu'un paiement, une commande ou une "
        "suppression devienne définitif.",
    ),
    CriterionInfo(
        "11.13",
        "La finalité d'un champ de saisie peut-elle être déduite pour faciliter le remplissage automatique des "
        "champs avec les données de l'utilisateur ?",
        "Quand le navigateur reconnaît un champ (nom, adresse, téléphone), il peut le remplir tout seul : c'est une "
        "aide précieuse pour les personnes qui ont du mal à taper au clavier ou à retenir ces informations.",
    ),
    # ---- Thème 12 : navigation ----
    CriterionInfo(
        "12.1",
        "Chaque ensemble de pages dispose-t-il de deux systèmes de navigation différents, au moins "
        "(hors cas particuliers) ?",
        "Chacun ne trouve pas une page de la même façon : une personne qui a du mal avec les menus, qui se repère "
        "difficilement ou qui utilise un lecteur d'écran peut préférer un plan du site ou un moteur de recherche. "
        "Avec un seul moyen de navigation, certaines personnes ne trouvent pas ce qu'elles cherchent.",
    ),
    CriterionInfo(
        "12.2",
        "Dans chaque ensemble de pages, le menu et les barres de navigation sont-ils toujours à la même place "
        "(hors cas particuliers) ?",
        "Une personne malvoyante qui agrandit fortement l'écran, ou qui a des difficultés de mémoire ou de "
        "concentration, retient où se trouve le menu. S'il change de place d'une page à l'autre, elle doit le "
        "rechercher à chaque fois et risque de se perdre.",
    ),
    CriterionInfo(
        "12.3",
        "La page « plan du site » est-elle pertinente ?",
        "Le plan du site sert de sommaire à ceux qui se perdent dans les menus, notamment les personnes qui "
        "utilisent un lecteur d'écran. S'il est incomplet ou contient des liens cassés ou mal nommés, il les mène "
        "au mauvais endroit ou nulle part.",
    ),
    CriterionInfo(
        "12.4",
        "Dans chaque ensemble de pages, la page « plan du site » est-elle accessible à partir d’une "
        "fonctionnalité identique ?",
        "Une personne qui se repère difficilement, ou qui navigue au clavier ou avec un lecteur d'écran, apprend "
        "où se trouve le lien vers le plan du site. S'il change de forme ou de place selon les pages, ou s'il "
        "manque sur certaines, elle ne le retrouve plus.",
    ),
    CriterionInfo(
        "12.5",
        "Dans chaque ensemble de pages, le moteur de recherche est-il atteignable de manière identique ?",
        "Une personne qui se repère difficilement, ou qui navigue au clavier ou avec un lecteur d'écran, apprend "
        "où se trouve la recherche. Si elle change de forme ou de place selon les pages, ou disparaît sur "
        "certaines, elle perd du temps à la chercher, voire y renonce.",
    ),
    CriterionInfo(
        "12.6",
        "Les zones de regroupement de contenus présentes dans plusieurs pages web (zones d’en-tête, de navigation "
        "principale, de contenu principal, de pied de page et de moteur de recherche) peuvent-elles être atteintes "
        "ou évitées ?",
        "Une personne qui utilise un lecteur d'écran ou le clavier doit pouvoir sauter directement au menu, au "
        "contenu ou à la recherche. Sinon, elle doit traverser le haut de page, identique sur chaque page, avant "
        "d'arriver à ce qui l'intéresse.",
    ),
    CriterionInfo(
        "12.7",
        "Dans chaque page web, un lien d’évitement ou d’accès rapide à la zone de contenu principal est-il présent "
        "(hors cas particuliers) ?",
        "Une personne qui navigue au clavier passe d'un lien à l'autre avec la touche Tab. Sans lien « Aller au "
        "contenu » en haut de page, elle doit parcourir tout le menu, sur chaque page, avant d'atteindre le contenu.",
    ),
    CriterionInfo(
        "12.8",
        "Dans chaque page web, l’ordre de tabulation est-il cohérent ?",
        "Une personne qui navigue au clavier avance d'élément en élément avec la touche Tab. Si cet ordre saute "
        "d'un bout à l'autre de la page, elle perd le fil, peut oublier un champ d'un formulaire et ne comprend "
        "plus où elle se trouve.",
    ),
    CriterionInfo(
        "12.9",
        "Dans chaque page web, la navigation ne doit pas contenir de piège au clavier. Cette règle est-elle "
        "respectée ?",
        "Une personne qui ne peut pas utiliser de souris peut rester bloquée dans un élément (lecteur vidéo, carte, "
        "fenêtre) qu'elle ne parvient plus à quitter au clavier. Elle ne peut alors plus utiliser le reste de la "
        "page.",
    ),
    CriterionInfo(
        "12.10",
        "Dans chaque page web, les raccourcis clavier n’utilisant qu’une seule touche (lettre minuscule ou "
        "majuscule, ponctuation, chiffre ou symbole) sont-ils contrôlables par l’utilisateur ?",
        "Une personne qui dicte à voix haute peut déclencher sans le vouloir un raccourci d'une seule lettre, et "
        "une personne qui a des tremblements peut l'activer en frôlant une touche. Si on ne peut ni le désactiver "
        "ni le modifier, des actions se lancent sans qu'elle l'ait voulu.",
    ),
    CriterionInfo(
        "12.11",
        "Dans chaque page web, les contenus additionnels apparaissant au survol, à la prise de focus ou à "
        "l’activation d’un composant d’interface sont-ils si nécessaire atteignables au clavier ?",
        "Un sous-menu ou une bulle qui apparaît au passage de la souris doit aussi pouvoir être parcouru au "
        "clavier. Sinon, une personne qui ne peut pas utiliser de souris n'accède pas aux liens ou boutons qu'il "
        "contient.",
    ),
    # ---- Thème 13 : consultation ----
    CriterionInfo(
        "13.1",
        "Pour chaque page web, l’utilisateur a-t-il le contrôle de chaque limite de temps modifiant le contenu "
        "(hors cas particuliers) ?",
        "Une personne qui lit lentement, qui a du mal à se concentrer ou qui écoute la page avec un lecteur d'écran "
        "met plus de temps que les autres. Si la page se recharge ou si la session expire avant qu'elle ait fini, "
        "elle perd sa lecture ou ce qu'elle avait saisi.",
    ),
    CriterionInfo(
        "13.2",
        "Dans chaque page web, l’ouverture d’une nouvelle fenêtre ne doit pas être déclenchée sans action de "
        "l’utilisateur. Cette règle est-elle respectée ?",
        "Une personne aveugle ne voit pas qu'une nouvelle fenêtre s'est ouverte : elle se retrouve sur une autre "
        "page sans comprendre pourquoi, et le bouton « Retour » ne la ramène plus. Cela désoriente aussi les "
        "personnes qui se repèrent difficilement.",
    ),
    CriterionInfo(
        "13.3",
        "Dans chaque page web, chaque document bureautique en téléchargement possède-t-il, si nécessaire, une "
        "version accessible (hors cas particuliers) ?",
        "Un document PDF ou Word mal conçu peut être illisible pour un lecteur d'écran, ou lu dans le désordre. "
        "Sans autre version, une personne aveugle ou malvoyante n'a pas accès à son contenu.",
    ),
    CriterionInfo(
        "13.4",
        "Pour chaque document bureautique ayant une version accessible, cette version offre-t-elle la même "
        "information ?",
        "Les personnes aveugles ou malvoyantes lisent la version accessible à la place du document. S'il y manque "
        "des passages, des chiffres ou des liens, elles disposent de moins d'informations que les autres.",
    ),
    CriterionInfo(
        "13.5",
        "Dans chaque page web, chaque contenu cryptique (art ASCII, émoticône, syntaxe cryptique) a-t-il une "
        "alternative ?",
        "Un lecteur d'écran lit une émoticône comme « deux-points tiret parenthèse » et un dessin fait de "
        "caractères comme une suite de signes sans fin. Sans explication, une personne aveugle n'en comprend pas "
        "le sens.",
    ),
    CriterionInfo(
        "13.6",
        "Dans chaque page web, pour chaque contenu cryptique (art ASCII, émoticône, syntaxe cryptique) ayant une "
        "alternative, cette alternative est-elle pertinente ?",
        "Une personne aveugle ne connaît le sens d'une émoticône ou d'un dessin en caractères que par son "
        "explication. Si celle-ci est vague ou fausse, elle comprend mal le message, par exemple une ironie ou un "
        "avertissement.",
    ),
    CriterionInfo(
        "13.7",
        "Dans chaque page web, les changements brusques de luminosité ou les effets de flash sont-ils "
        "correctement utilisés ?",
        "Des flashs ou des clignotements rapides de lumière peuvent déclencher une crise chez une personne "
        "épileptique, même si elle ne regarde l'écran que quelques secondes. Ils provoquent aussi des maux de tête "
        "ou des malaises chez d'autres personnes.",
    ),
    CriterionInfo(
        "13.8",
        "Dans chaque page web, chaque contenu en mouvement ou clignotant est-il contrôlable par l’utilisateur ?",
        "Un texte qui défile ou un élément qui clignote sans arrêt empêche de se concentrer, notamment les "
        "personnes qui ont des troubles de l'attention, et un texte qui bouge est difficile à lire pour les "
        "personnes malvoyantes ou qui lisent lentement. Sans bouton pour l'arrêter, elles ne peuvent pas s'en "
        "protéger.",
    ),
    CriterionInfo(
        "13.9",
        "Dans chaque page web, le contenu proposé est-il consultable quelle que soit l’orientation de l’écran "
        "(portrait ou paysage) (hors cas particuliers) ?",
        "Certaines personnes ne peuvent pas tourner leur appareil, par exemple quand leur tablette est fixée à un "
        "fauteuil roulant. Si la page ne s'affiche que dans un sens, elles ne peuvent pas la consulter.",
    ),
    CriterionInfo(
        "13.10",
        "Dans chaque page web, les fonctionnalités utilisables ou disponibles au moyen d’un geste complexe "
        "peuvent-elles être également disponibles au moyen d’un geste simple (hors cas particuliers) ?",
        "Pincer l'écran avec deux doigts ou faire glisser un doigt selon un tracé précis est difficile, voire "
        "impossible, pour une personne qui a des tremblements ou qui n'utilise qu'un doigt ou un stylet. Sans "
        "bouton qui fait la même chose, elle ne peut pas utiliser la fonctionnalité.",
    ),
    CriterionInfo(
        "13.11",
        "Dans chaque page web, les actions déclenchées au moyen d’un dispositif de pointage sur un point unique "
        "de l’écran peuvent-elles faire l’objet d’une annulation (hors cas particuliers) ?",
        "Une personne qui a des gestes imprécis touche souvent le mauvais bouton. Si l'action se lance dès le "
        "contact, avant que le doigt ou le bouton de la souris soit relâché, elle ne peut pas se rattraper et "
        "subit une action qu'elle n'a pas voulue, comme une suppression.",
    ),
    CriterionInfo(
        "13.12",
        "Dans chaque page web, les fonctionnalités qui impliquent un mouvement de l’appareil ou vers l’appareil "
        "peuvent-elles être satisfaites de manière alternative (hors cas particuliers) ?",
        "Secouer ou incliner le téléphone est impossible pour une personne dont l'appareil est fixé, ou qui ne "
        "peut pas bouger les mains facilement. À l'inverse, une personne qui a des tremblements peut déclencher "
        "l'action sans le vouloir : il faut un bouton qui fasse la même chose et un moyen de couper la détection.",
    ),
)

CRITERIA: dict[str, CriterionInfo] = {entry.criterion_id: entry for entry in _ENTRIES}


def criterion_info(criterion_id: str) -> CriterionInfo | None:
    """Explications du critère ``criterion_id`` (par exemple "2.1"), ou None s'il n'est pas renseigné."""
    return CRITERIA.get(criterion_id)
