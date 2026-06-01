---
theme: default
title: "Parler à son infrastructure"
info: |
  IA-NA 2026 — La Rochelle
  par Samir Akarioh — Developer Advocate @ Scalingo
class: text-center
highlighter: shiki
mdc: true
layout: cover
routerMode: hash
---

<div class="flex flex-col items-center justify-center h-full gap-4 px-8">
<h1 class="text-4xl font-black text-white leading-tight text-center mt-2">
  Parler à son infrastructure<br>construire un agent DevOps conversationnel
</h1>
<div class="flex items-center gap-4 mt-4 s-card px-6 py-3">
  <div class="w-11 h-11 rounded-full flex items-center justify-center text-lg font-black text-white shrink-0" style="background: linear-gradient(135deg, #f65516, #3d1fc8);">SA</div>
  <div class="text-left">
    <div class="font-semibold text-white text-sm">Samir Akarioh</div>
    <div class="text-xs s-muted">Developer Advocate @ <span class="s-accent font-semibold">Scalingo</span> · IA-NA 2026, La Rochelle</div>
  </div>
</div>
</div>

---
layout: center
---

## Agenda des 45 minutes

<div class="grid grid-cols-2 gap-5 mt-8 max-w-5xl mx-auto text-sm">
  <div class="s-card s-card-orange">
    <div class="font-semibold text-white mb-2">00–05 min</div>
    <div class="s-muted">Le sujet, le contexte et la promesse produit.</div>
  </div>
  <div class="s-card s-card-violet">
    <div class="font-semibold text-white mb-2">05–12 min</div>
    <div class="s-muted">Pourquoi parler à son infra semble simple, mais ne l'est pas du tout.</div>
  </div>
  <div class="s-card">
    <div class="font-semibold text-white mb-2">12–25 min</div>
    <div class="s-muted">Le système réel : nLU, orchestration, API Scalingo, WebSocket, Celery, Redis et décisions métier.</div>
  </div>
  <div class="s-card s-card-green">
    <div class="font-semibold text-white mb-2">25–35 min</div>
    <div class="s-muted">Démo live : lecture de logs, clarification, sécurité et observabilité.</div>
  </div>
  <div class="s-card s-card-yellow col-span-2">
    <div class="font-semibold text-white mb-2">35–45 min</div>
    <div class="s-muted">Ce que j'ai appris : architecture de contrôle, limites réelles et ce qu'il ne faut surtout pas automatiser naïvement.</div>
  </div>
</div>

---
layout: center
---

## Qui suis-je ?

<div class="mt-5 grid grid-cols-2 gap-4 max-w-4xl mx-auto">
  <div class="flex items-center gap-3 s-card s-card-orange px-4 py-4">
    <span class="text-2xl">☁️</span>
    <div>
      <div class="font-semibold text-white text-sm">Developer Advocate @ <span class="s-accent">Scalingo</span></div>
      <div class="s-muted text-xs">Cloud, DX, démos, architecture, talks</div>
    </div>
  </div>
  <div class="flex items-center gap-3 s-card px-4 py-4">
    <span class="text-2xl">🛠️</span>
    <div>
      <div class="font-semibold text-white text-sm">Builder</div>
      <div class="s-muted text-xs">Je construis des prototypes qui doivent survivre au contact du réel</div>
    </div>
  </div>
  <div class="flex items-center gap-3 s-card px-4 py-4">
    <span class="text-2xl">🎤</span>
    <div>
      <div class="font-semibold text-white text-sm">Speaker</div>
      <div class="s-muted text-xs">Je parle souvent de cloud, d'IA appliquée et d'outils pour développeurs</div>
    </div>
  </div>
  <div class="flex items-center gap-3 s-card s-card-violet px-4 py-4">
    <span class="text-2xl">🔐</span>
    <div>
      <div class="font-semibold text-white text-sm">Obsession perso</div>
      <div class="s-muted text-xs">Faire des démos impressionnantes sans mentir sur les contraintes de prod</div>
    </div>
  </div>
</div>

---
layout: center
---

## C'est quoi Scalingo ?

<div class="mt-6 grid grid-cols-3 gap-5 max-w-5xl mx-auto text-sm">
  <div class="s-card s-card-orange p-5 text-center">
    <div class="text-3xl mb-2">☁️</div>
    <div class="font-semibold">Un PaaS européen</div>
    <div class="s-muted mt-2">Déployer, exécuter et faire évoluer des applications sans gérer soi-même les serveurs</div>
  </div>
  <div class="s-card s-card-violet p-5 text-center">
    <div class="text-3xl mb-2">🗄️</div>
    <div class="font-semibold">Apps + DBaaS</div>
    <div class="s-muted mt-2">Applications, bases managées, réseau, logs, scaling, opérations quotidiennes</div>
  </div>
  <div class="s-card s-card-green p-5 text-center">
    <div class="text-3xl mb-2">🛡️</div>
    <div class="font-semibold">Souveraineté & conformité</div>
    <div class="s-muted mt-2">Positionnement européen avec sécurité et conformité intégrées à la plateforme</div>
  </div>
</div>

<div class="mt-8 s-card max-w-4xl mx-auto text-sm text-center">
 <span class="s-accent font-semibold">Scalingo = un PaaS qui prend en charge le runtime, le réseau, les logs, le scaling et une partie importante des opérations</span> pour que les équipes se concentrent sur l'application.
</div>

---
layout: section
---

# Acte 1

## Et si l'infra devenait conversationnelle ?

---
layout: center
---

## La promesse produit

<div class="mt-6 space-y-4 max-w-3xl mx-auto text-lg">
  <div class="s-card px-5 py-4">🧾 « Crée-moi une app de démo pour mon workshop Go »</div>
  <div class="s-card px-5 py-4">📈 « Scale le worker à 2 instances pendant 30 minutes »</div>
  <div class="s-card px-5 py-4">📜 « Montre-moi les logs de l'app checkout sur les 10 dernières minutes »</div>
  <div class="s-card px-5 py-4">🔐 « Change la variable d'environnement FEATURE_FLAG_BETA à true »</div>
</div>

<div class="mt-8 text-center s-accent text-xl font-semibold">
  Une seule phrase. Plusieurs opérations possibles. Et beaucoup de responsabilités derrière.
</div>

---
layout: center
---

## Le vrai problème

<div class="mt-6 grid grid-cols-3 gap-5 max-w-5xl mx-auto text-sm">
  <div class="s-card s-card-green p-5 text-center">
    <div class="text-3xl mb-2">💬</div>
    <div class="font-semibold text-green-300">Comprendre</div>
    <div class="s-muted mt-2">Identifier ce que l'utilisateur veut vraiment dire.</div>
  </div>
  <div class="s-card s-card-yellow p-5 text-center">
    <div class="text-3xl mb-2">🧠</div>
    <div class="font-semibold text-yellow-300">Décider</div>
    <div class="s-muted mt-2">Choisir entre exécuter, clarifier ou refuser.</div>
  </div>
  <div class="s-card s-card-red p-5 text-center">
    <div class="text-3xl mb-2">⚠️</div>
    <div class="font-semibold text-red-400">Assumer</div>
    <div class="s-muted mt-2">Porter les conséquences d'une action d'infrastructure réelle.</div>
  </div>
</div>

<div class="mt-8 s-card max-w-4xl mx-auto text-sm text-center">
  Le langage naturel n'est que la surface du produit. Le vrai sujet, c'est <span class="s-accent font-semibold">la politique de décision</span> derrière chaque phrase.
</div>

---
layout: center
---

## Ce que l'utilisateur voit vs ce qui se passe

<div class="mt-6 grid grid-cols-2 gap-6 max-w-5xl mx-auto">
  <div class="s-card s-card-green p-6">
    <div class="text-2xl mb-3">😊</div>
    <div class="font-semibold text-green-300">Ce que l'utilisateur voit</div>
    <div class="s-muted text-sm mt-2">Une conversation naturelle, courte, presque banale, avec une réponse immédiate et actionnable.</div>
  </div>
  <div class="s-card s-card-red p-6">
    <div class="text-2xl mb-3">😅</div>
    <div class="font-semibold text-red-400">Ce qui se passe réellement</div>
    <div class="s-muted text-sm mt-2">Classification d'intention, extraction d'entités, validation du contrat, mapping métier, appel API authentifié, gestion d'erreurs, audit et reformulation.</div>
  </div>
</div>

---
layout: center
---

## Les 3 sorties possibles

<div class="mt-6 grid grid-cols-3 gap-5 max-w-5xl mx-auto text-sm">
  <div class="s-card s-card-green p-5 text-center">
    <div class="text-3xl mb-2">✅</div>
    <div class="font-semibold text-green-300">Exécuter</div>
    <div class="s-muted mt-2">Quand l'intention est claire, les paramètres sont complets et l'action autorisée.</div>
  </div>
  <div class="s-card s-card-yellow p-5 text-center">
    <div class="text-3xl mb-2">🤔</div>
    <div class="font-semibold text-yellow-300">Clarifier</div>
    <div class="s-muted mt-2">Quand il manque une information ou qu'une ambiguïté peut conduire à la mauvaise action.</div>
  </div>
  <div class="s-card s-card-red p-5 text-center">
    <div class="text-3xl mb-2">⛔</div>
    <div class="font-semibold text-red-400">Refuser</div>
    <div class="s-muted mt-2">Quand la demande est trop risquée, hors scope ou insuffisamment fiable.</div>
  </div>
</div>

---
layout: center
---

## Pourquoi un PaaS est un bon terrain pour ce projet

<div class="mt-6 grid grid-cols-2 gap-6 max-w-4xl mx-auto text-sm">
  <div class="s-card s-card-green p-6">
    <div class="font-semibold text-green-300 mb-2">Surface d'action claire</div>
    <div class="s-muted">Créer une app, lire des logs, scaler des process, gérer des variables d'environnement : ce sont des actions concrètes, compréhensibles et démontrables.</div>
  </div>
  <div class="s-card s-card-orange p-6">
    <div class="font-semibold text-white mb-2">API exploitable</div>
    <div class="s-muted">Chaque phrase utilisateur peut être traduite en un appel déterministe à l'API, ce qui permet de séparer clairement compréhension du langage et exécution métier.</div>
  </div>
</div>

---
layout: center
---

## Ce que l'agent peut faire — et ce qu'il ne fera jamais

<div class="mt-6 grid grid-cols-3 gap-5 max-w-6xl mx-auto text-sm">
  <div class="s-card s-card-green p-5">
    <div class="font-semibold text-green-300 mb-3">Autorisé</div>
    <div class="s-muted space-y-2">
      <div>Lire des logs</div>
      <div>Créer une app de démo</div>
      <div>Scaler un process borné</div>
    </div>
  </div>
  <div class="s-card s-card-yellow p-5">
    <div class="font-semibold text-yellow-300 mb-3">Sous conditions</div>
    <div class="s-muted space-y-2">
      <div>Modifier une variable</div>
      <div>Action avec confirmation explicite</div>
      <div>Clarification si paramètres incomplets</div>
    </div>
  </div>
  <div class="s-card s-card-red p-5">
    <div class="font-semibold text-red-400 mb-3">Interdit / refusé</div>
    <div class="s-muted space-y-2">
      <div>Action destructive hors scope</div>
      <div>Demande trop ambiguë</div>
      <div>Commande incompatible avec la politique métier</div>
    </div>
  </div>
</div>

<div class="mt-8 s-card max-w-4xl mx-auto text-sm text-center">
  Un agent DevOps crédible n'est pas défini par tout ce qu'il peut faire, mais par la précision avec laquelle on borne <span class="s-accent font-semibold">son autorité</span>.
</div>

---
layout: section
---

# Acte 2

## Comprendre une phrase, ce n'est pas agir

---
layout: center
---

## Le projet réel : un monorepo, deux apps

```text
chatbotsamirrasa/
├── api-app/   → interface, websocket, orchestration, actions Scalingo
├── nlu-app/   → compréhension du langage, contrat /model/parse v3
└── slides/    → support de démonstration
```

<div class="mt-6 grid grid-cols-2 gap-5 max-w-4xl mx-auto text-sm">
  <div class="s-card s-card-orange">
    <div class="font-semibold text-white mb-2">api-app</div>
    <div class="s-muted">FastAPI, WebSocket, Celery, Redis, client HTTP Scalingo, orchestration conversationnelle et exécution des actions.</div>
  </div>
  <div class="s-card s-card-violet">
    <div class="font-semibold text-white mb-2">nlu-app</div>
    <div class="s-muted">FastAPI + Transformers + Torch pour exposer un service nLU auto-hébergé avec <code>GET /status</code> et <code>POST /model/parse</code>.</div>
  </div>
</div>

---
layout: center
---

## Pourquoi ne pas utiliser un service NLU externe ?

<div class="mt-6 grid grid-cols-2 gap-6 max-w-4xl mx-auto text-sm">
  <div class="s-card s-card-violet p-6">
    <div class="font-semibold text-white mb-2">Maîtrise</div>
    <div class="s-muted">Tu contrôles le contrat, les modèles, la calibration, les seuils, la latence et l'évolution du service sans dépendre d'un fournisseur tiers pour la compréhension métier.</div>
  </div>
  <div class="s-card s-card-orange p-6">
    <div class="font-semibold text-white mb-2">Cohérence produit</div>
    <div class="s-muted">Pour un assistant DevOps, la compréhension de requêtes très spécifiques vaut souvent mieux qu'un service plus généraliste mais moins prédictible sur le domaine.</div>
  </div>
</div>

---
layout: center
---

## Pourquoi un LLM seul ne suffit pas

<div class="mt-6 grid grid-cols-2 gap-5 max-w-4xl mx-auto text-sm">
  <div class="s-card s-card-violet p-5">
    <div class="font-semibold text-white mb-2">Ce qu'on veut</div>
    <div class="s-muted">Une sortie structurée, stable, testable, calibrée et exploitable par une couche métier.</div>
  </div>
  <div class="s-card s-card-orange p-5">
    <div class="font-semibold text-white mb-2">Ce qu'on ne veut pas</div>
    <div class="s-muted">Une phrase jolie mais floue, difficile à valider, à scorer et à transformer en action d'infrastructure sûre.</div>
  </div>
</div>

<div class="mt-8 s-card max-w-4xl mx-auto text-sm text-center">
  Un LLM seul est très bon pour générer. Ici, on lui demande surtout de <span class="s-accent font-semibold">décider proprement</span>.
</div>

---
layout: center
---

## Ce que le modèle doit faire exactement

<div class="mt-6 grid grid-cols-3 gap-4 max-w-5xl mx-auto text-sm">
  <div class="s-card s-card-red p-4">
    <div class="text-red-400 font-semibold mb-2">Intent</div>
    <div class="s-muted">Décider s'il s'agit de créer, lire, scaler, modifier ou refuser.</div>
  </div>
  <div class="s-card s-card-yellow p-4">
    <div class="text-yellow-300 font-semibold mb-2">Entities</div>
    <div class="s-muted">Identifier l'application, le process, la valeur, la durée, l'environnement et d'autres paramètres utiles.</div>
  </div>
  <div class="s-card s-card-green p-4">
    <div class="text-green-300 font-semibold mb-2">Confidence</div>
    <div class="s-muted">Fournir un score suffisant pour décider entre exécuter, clarification ou refus.</div>
  </div>
</div>

<div class="mt-8 s-card max-w-4xl mx-auto text-sm">
  Le modèle n'est pas là pour “parler joliment”. Il est là pour produire une décision exploitable par un système d'orchestration.
</div>

---
layout: center
---

## Les variables qui changent tout

<div class="mt-6 grid grid-cols-2 gap-5 max-w-4xl mx-auto text-sm">
  <div class="s-card s-card-violet">
    <div class="font-semibold text-white mb-2">Côté nLU</div>
    <div class="s-muted"><code>INTENT_MIN_CONFIDENCE=0.45</code>, <code>INTENT_MIN_MARGIN=0.08</code>, <code>INTENT_TOPK=3</code>, <code>NLU_CALIBRATION_ENABLED=true</code>.</div>
  </div>
  <div class="s-card s-card-orange">
    <div class="font-semibold text-white mb-2">Côté API</div>
    <div class="s-muted"><code>NLU_EXPECTED_CONTRACT=v3</code>, <code>RASA_TIMEOUT_MS=3000</code>, <code>NLU_CLARIFICATION_TOPK=3</code>, fallback regex si nécessaire.</div>
  </div>
</div>

<div class="mt-8 text-center text-lg s-accent font-semibold">
  Ces paramètres sont plus importants pour la fiabilité du produit que le nom marketing exact du modèle.
</div>

---
layout: center
---

## Le pipeline de décision

<div class="mt-6 flex flex-col gap-4 max-w-4xl mx-auto text-sm">
  <div class="s-card px-5 py-4"><span class="s-tag mr-3">Step 1</span> La phrase utilisateur arrive via HTTP ou WebSocket dans <code>api-app</code>.</div>
  <div class="s-card px-5 py-4"><span class="s-tag mr-3">Step 2</span> L'API appelle le service nLU sur <code>POST /model/parse</code> avec contrat attendu <code>v3</code>.</div>
  <div class="s-card px-5 py-4"><span class="s-tag mr-3">Step 3</span> Le résultat contient intention, entités et score; la couche métier décide s'il faut exécuter, clarifier ou refuser.</div>
  <div class="s-card px-5 py-4"><span class="s-tag mr-3">Step 4</span> L'action validée est transformée en appel vers l'API Scalingo via un client HTTP avec Bearer token, retry et mapping d'erreurs.</div>
  <div class="s-card px-5 py-4"><span class="s-tag mr-3">Step 5</span> La réponse est reformulée pour l'utilisateur avec retour d'état, logs, confirmation ou demande de précision.</div>
</div>

---
layout: center
---

## Une commande réelle de la démo

<div class="mt-8 max-w-5xl mx-auto">
  <div class="s-card s-card-orange p-6 text-lg">
    <div class="font-semibold text-white mb-3">Phrase utilisateur</div>
    <div class="text-white leading-relaxed">
      « Montre-moi les logs de l'app
      <span class="s-accent font-semibold">checkout</span>
      sur les
      <span class="s-accent font-semibold">10 dernières minutes</span> »
    </div>
  </div>

  <div class="grid grid-cols-3 gap-4 mt-6 text-sm">
    <div class="s-card p-4">
      <div class="font-semibold text-white mb-2">Ce que l'utilisateur veut</div>
      <div class="s-muted">Consulter rapidement l'état de son application sans naviguer dans le dashboard ni mémoriser une commande CLI.</div>
    </div>
    <div class="s-card p-4">
      <div class="font-semibold text-white mb-2">Ce qui doit être compris</div>
      <div class="s-muted">L'action visée, la cible exacte, la fenêtre temporelle et le niveau de confiance suffisant pour agir.</div>
    </div>
    <div class="s-card s-card-violet p-4">
      <div class="font-semibold text-white mb-2">Pourquoi c'est intéressant</div>
      <div class="s-muted">Cette phrase paraît triviale, mais elle doit devenir une requête structurée et sûre avant toute exécution.</div>
    </div>
  </div>
</div>

---
layout: center
---

## Ce que le modèle comprend

<div class="mt-6 grid grid-cols-2 gap-6 max-w-5xl mx-auto text-sm">
  <div class="s-card s-card-violet p-5">
    <div class="font-semibold text-white mb-3">Sortie attendue du service nLU</div>

```json
{
  "intent": "read_logs",
  "confidence": 0.94,
  "entities": {
    "app": "checkout",
    "time_range": "10 minutes"
  }
}
```

  </div>

  <div class="s-card p-5">
    <div class="font-semibold text-white mb-3">Comment lire cette sortie</div>
    <div class="space-y-3 s-muted">
      <div><span class="text-white font-semibold">intent</span> : l'objectif de la phrase, ici consulter des logs</div>
      <div><span class="text-white font-semibold">entities</span> : les paramètres extraits, ici <code>checkout</code> et <code>10 minutes</code></div>
      <div><span class="text-white font-semibold">confidence</span> : le score qui permet de choisir entre exécuter, clarifier ou refuser</div>
    </div>
  </div>
</div>

<div class="mt-8 s-card max-w-4xl mx-auto text-sm">
  Le modèle ne “fait” pas l'action : il produit une décision structurée que la couche métier peut convertir en exécution réelle.
</div>

---
layout: center
---

## Ce que l'application fait ensuite

<div class="mt-6 flex flex-col gap-4 max-w-4xl mx-auto text-sm">
  <div class="s-card px-5 py-4"><span class="s-tag mr-3">Étape 1</span> Vérifier que <code>checkout</code> correspond bien à une application connue et autorisée.</div>
  <div class="s-card px-5 py-4"><span class="s-tag mr-3">Étape 2</span> Transformer <code>10 dernières minutes</code> en paramètres exploitables pour la récupération de logs.</div>
  <div class="s-card px-5 py-4"><span class="s-tag mr-3">Étape 3</span> Obtenir l'accès aux logs de l'application via la couche API / logs de la plateforme.</div>
  <div class="s-card px-5 py-4"><span class="s-tag mr-3">Étape 4</span> Retourner les logs à l'utilisateur avec une réponse conversationnelle propre et traçable.</div>
</div>

<div class="mt-8 grid grid-cols-2 gap-5 max-w-5xl mx-auto text-sm">
  <div class="s-card s-card-green p-5">
    <div class="font-semibold text-green-300 mb-2">Si tout est clair</div>
    <div class="s-muted">Le système exécute la lecture des logs avec une réponse lisible pour l'utilisateur.</div>
  </div>
  <div class="s-card s-card-yellow p-5">
    <div class="font-semibold text-yellow-300 mb-2">Si quelque chose manque</div>
    <div class="s-muted">Le système clarifie plutôt que de deviner l'application cible, la période, ou le type de logs attendu.</div>
  </div>
</div>

---
layout: center
---

## Pourquoi WebSocket + Celery ?

<div class="mt-6 grid grid-cols-2 gap-6 max-w-4xl mx-auto text-sm">
  <div class="s-card s-card-violet p-6">
    <div class="font-semibold text-white mb-2">WebSocket</div>
    <div class="s-muted">Pour garder une sensation conversationnelle, pousser les messages en temps réel et éviter l'effet “submit form / wait / refresh”.</div>
  </div>
  <div class="s-card s-card-orange p-6">
    <div class="font-semibold text-white mb-2">Celery + Redis</div>
    <div class="s-muted">Pour sortir du thread web les opérations plus lourdes ou plus lentes, mieux isoler les traitements et garder une API réactive.</div>
  </div>
</div>

---
layout: center
---

## Déployer les deux apps sur Scalingo

<div class="mt-6 grid grid-cols-2 gap-5 max-w-5xl mx-auto text-sm">
  <div class="s-card s-card-violet">
    <div class="font-semibold text-white mb-2">nlu-app</div>
    <div class="s-muted">Déploiement séparé avec version du contrat, modèle, calibration, seuils d'intention et token d'auth éventuel.</div>
  </div>
  <div class="s-card s-card-orange">
    <div class="font-semibold text-white mb-2">api-app</div>
    <div class="s-muted">Déploiement séparé avec token API Scalingo, Redis, URL du service nLU, timeout, fallback regex, top-K de clarification et concurrence web/worker.</div>
  </div>
</div>

```bash
scalingo --app chatbotsamir-api scale worker:1
```

---
layout: section
---

# Acte 3

## Démo, safety et réalité du produit

---
layout: center
---

## Plan de démo live

<div class="mt-6 grid grid-cols-2 gap-5 max-w-4xl mx-auto text-sm">
  <div class="s-card">
    <div class="font-semibold text-white mb-2">Démo 1 — Lecture de logs</div>
    <div class="s-muted">Prendre exactement la commande analysée juste avant, puis montrer le résultat réel côté système.</div>
  </div>
  <div class="s-card">
    <div class="font-semibold text-white mb-2">Démo 2 — Ambiguïté</div>
    <div class="s-muted">Montrer un cas où le système ne déclenche pas l'action tout de suite et demande une clarification.</div>
  </div>
  <div class="s-card">
    <div class="font-semibold text-white mb-2">Démo 3 — Safety</div>
    <div class="s-muted">Refuser une action trop risquée, ou demander une confirmation explicite avant une modification sensible.</div>
  </div>
  <div class="s-card">
    <div class="font-semibold text-white mb-2">Démo 4 — Observabilité</div>
    <div class="s-muted">Afficher le pipeline : phrase → parse nLU → décision → appel API → réponse utilisateur.</div>
  </div>
</div>

---
layout: center
---

## Là où ça casse en prod

<div class="mt-6 grid grid-cols-2 gap-5 max-w-5xl mx-auto text-sm">
  <div class="s-card s-card-red p-5">
    <div class="font-semibold text-red-400 mb-2">Mauvaise cible</div>
    <div class="s-muted">La phrase semble correcte, mais l'app ou le process identifiés ne sont pas les bons.</div>
  </div>
  <div class="s-card s-card-red p-5">
    <div class="font-semibold text-red-400 mb-2">Confiance trompeuse</div>
    <div class="s-muted">Le modèle a l'air sûr de lui, mais il manque un paramètre critique.</div>
  </div>
  <div class="s-card s-card-yellow p-5">
    <div class="font-semibold text-yellow-300 mb-2">Action sensible</div>
    <div class="s-muted">Une lecture de logs est bénigne; une modification de variable ou de scaling ne l'est pas forcément.</div>
  </div>
  <div class="s-card s-card-orange p-5">
    <div class="font-semibold text-white mb-2">Échec partiel</div>
    <div class="s-muted">Le nLU répond, mais l'API métier timeoute, ou l'utilisateur reçoit un résultat mal expliqué.</div>
  </div>
</div>

---
layout: center
---

## Les garde-fous du système

<div class="mt-5 grid grid-cols-5 gap-3 max-w-5xl mx-auto text-xs text-center">
  <div class="s-card p-4"><div class="text-2xl mb-2">1</div><div class="font-semibold">Contrat versionné</div><div class="s-muted mt-1"><code>X-NLU-Contract: v3</code></div></div>
  <div class="s-card p-4"><div class="text-2xl mb-2">2</div><div class="font-semibold">Seuils & marge</div><div class="s-muted mt-1">Confiance minimale et ambiguïté détectée</div></div>
  <div class="s-card p-4"><div class="text-2xl mb-2">3</div><div class="font-semibold">Clarification</div><div class="s-muted mt-1">Top-K intentions avant action risquée</div></div>
  <div class="s-card p-4"><div class="text-2xl mb-2">4</div><div class="font-semibold">Timeout & retry</div><div class="s-muted mt-1">Appels maîtrisés vers NLU et API</div></div>
  <div class="s-card p-4"><div class="text-2xl mb-2">5</div><div class="font-semibold">Scopes métier</div><div class="s-muted mt-1">Ce que l'agent peut faire, et surtout ne pas faire</div></div>
</div>

---
layout: center
---

## Conclusion

<div class="max-w-4xl mx-auto mt-10 text-center">
  <div class="text-3xl font-black text-white leading-tight">
    Le jour où une phrase peut modifier votre infrastructure,<br>la question n'est plus seulement <span class="s-accent">« est-ce qu'elle comprend ? »</span>
  </div>

  <div class="mt-8 text-2xl s-muted">
    La vraie question est :<br><span class="text-white font-semibold">est-ce qu'elle mérite d'être transformée en action ?</span>
  </div>

  <div class="mt-10 s-card inline-block px-8 py-4">
    Samir Akarioh · <span class="s-accent">Scalingo</span>
  </div>
</div>