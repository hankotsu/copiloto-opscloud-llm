# Guía: publicar el proyecto en GitHub

Pasos en orden. Los comandos van para **Windows (PowerShell)** y **Linux/macOS** donde cambian.

## 0. Confirmar con el docente (antes de crear nada)

- ¿Repositorio **público** o **privado**? Si es privado: ¿a qué usuario de GitHub hay que darle acceso?
- ¿Repositorio propio o *fork* del repo del curso?
- ¿Fecha de entrega y qué se entrega exactamente: enlace al repo, a un *tag* o *release*, o al video?

## 1. Preparar la cuenta de GitHub (una sola vez)

1. Activa la **verificación en dos pasos** (Settings → Password and authentication).
2. Oculta tu correo: Settings → Emails → marca **Keep my email addresses private** y **Block command line pushes that expose my email**. Copia la dirección `…@users.noreply.github.com` que aparece ahí.

## 2. Instalar herramientas

| Herramienta | Para qué | Windows | macOS |
|---|---|---|---|
| Git | Control de versiones | `winget install Git.Git` | `brew install git` |
| GitHub CLI | Autenticarse y crear el repo | `winget install GitHub.cli` | `brew install gh` |
| Python 3.12 | Backend, generador y tests | `winget install Python.Python.3.12` | `brew install python@3.12` |
| Ollama | Modelo local | ollama.com/download | ollama.com/download |

Después, cierra y vuelve a abrir la terminal.

## 3. Configurar Git y autenticarte

```bash
git config --global user.name "Hans Berrocal Carranza"
git config --global user.email "<ID>+<USUARIO>@users.noreply.github.com"
git config --global init.defaultBranch main
gh auth login          # GitHub.com → HTTPS → Login with a web browser
```

## 4. Preparar el proyecto local

```bash
cd copiloto-opscloud-llm
python -m venv .venv
# Windows:  .venv\Scripts\activate      Linux/macOS:  source .venv/bin/activate
pip install -r requirements-dev.txt
python data_gen/generar_dataset_sintetico.py
pytest -q                                   # debe terminar en "36 passed"
```

## 5. Configurar la guardia de confidencialidad

Crea el archivo **`.confidencial.txt`** en la raíz, con una palabra por línea: nombres de clientes y empleadores, dominios de correo, namespaces de tenancy, prefijos de nombres de recursos reales, etc. Ese archivo está en `.gitignore` **y nunca se sube**, porque publicar la lista ya sería una filtración.

```bash
python scripts/verificar_confidencialidad.py   # debe decir "Confidencialidad OK (N palabras vigiladas)"
pre-commit install                             # activa los controles en cada commit
pre-commit run --all-files                     # la primera vez descarga gitleaks
```

## 6. Primer commit

```bash
git init
git add .
git status        # revisa: NO deben aparecer data/, .env, .confidencial.txt, *.sqlite ni *.xlsx
git commit -m "Base: dataset sintético, backend, verificador, evaluación e interfaz"
```

Si `pre-commit` bloquea el commit, corrige lo que indique y repite `git add .` y `git commit`.

## 7. Crear el repositorio y subir el código

```bash
gh repo create copiloto-opscloud-llm --public --source . --remote origin --push
# o --private si así lo pide el docente
```

## 8. Ajustes en la web de GitHub

1. **Settings → Secrets and variables → Actions → New repository secret**: crea `PALABRAS_PROHIBIDAS` con las mismas palabras de `.confidencial.txt`, separadas por comas.
2. **Settings → Code security**: confirma que *Secret scanning* y *Push protection* estén activos.
3. **Actions**: vuelve a correr el workflow (*Re-run all jobs*) para que tome el secreto. Ambos jobs deben quedar en verde.
4. En `README.md`, reemplaza `<TU_USUARIO>` por tu usuario para que se vea la insignia de CI. Haz commit y push.
5. Si el repo es privado: **Settings → Collaborators → Add people** → el usuario del docente.

## 9. Trabajo diario

```bash
git add . && git commit -m "<qué hiciste y por qué>" && git push
git tag -a v0.4 -m "Evaluación completa" && git push --tags      # solo en los hitos marcados en la guía
```

Commits pequeños y frecuentes: el historial también es evidencia del trabajo. Los commits y tags de cada día están en [`GUIA_IMPLEMENTACION.md`](GUIA_IMPLEMENTACION.md).

## 10. Entrega

1. Sube el video a YouTube como **no listado** (o a Drive con acceso por enlace) y pon el enlace en el README. **No subas el video al repo**: GitHub rechaza archivos de más de 100 MB.
2. Versiona en `eval/resultados/` los resultados de la evaluación (CSV/JSON pequeños).
3. Prueba desde cero, como lo haría el docente: clona el repo en otra carpeta y sigue el README al pie de la letra.
4. Crea la versión final: `gh release create v1.0 --title "Entrega final" --notes "Proyecto final del curso"`.
5. Envía el enlace del repositorio y el del release `v1.0`.

## Si se filtra un secreto

1. **Revoca la API key de inmediato** en el panel del proveedor. Esto es lo único que realmente la invalida.
2. Genera una nueva, guárdala solo en `.env` y revisa el uso facturado de la key filtrada.
3. Borrarla del historial (`git filter-repo`) es opcional y posterior: la key ya debe considerarse comprometida.
