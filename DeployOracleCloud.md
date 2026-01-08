# Déploiement Oracle Cloud

## IP Production
132.226.96.197

## Commandes d'installation
[Colle ton historique ici]

## Commandes utiles
```bash
# Se connecter
ssh -i ~/.ssh/ssh-key-*.key ubuntu@132.226.96.197

# Voir les logs
docker-compose logs -f

# Redémarrer
docker-compose restart

# Arrêter
docker-compose down

# Relancer
docker-compose up -d
```

**Sauvegarde et commit:**
```bash
git add DEPLOY.md
git commit -m "Add deployment instructions"
git push
```

---

## Avant de déconnecter du serveur:
```bash
# Vérifie qu'Apollo tourne
docker-compose ps

# Puis déconnecte
exit
```

**Apollo continuera à tourner en arrière-plan! ✅**

Tu veux que je te crée le fichier DEPLOY.md complet?