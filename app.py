import json
import os
from datetime import datetime
from functools import wraps

import anthropic
from dotenv import load_dotenv

load_dotenv()
from flask import Flask, abort, redirect, render_template, request, session, url_for
from models import (
    BaseInfo,
    Friend,
    Idea,
    Location,
    MaterialItem,
    Project,
    ProjectAssignment,
    Vote,
    db,
)

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

IDEA_SEED = [
    # Farms
    ("Iron Farm", "Farms", "Automated iron from zombie villagers"),
    ("Villager Breeder", "Farms", "Grow a workforce for trading halls"),
    ("Crop Farm", "Farms", "Auto-harvesting wheat/carrot/potato field"),
    ("General Mob Farm", "Farms", "Dark room or spawner grinder for XP and drops"),
    ("Bamboo/Sugarcane Farm", "Farms", "Renewable building material and fuel"),
    ("Honey Farm", "Farms", "Bee boxes for honey and honeycomb"),
    ("Kelp Farm", "Farms", "Auto-smelting fuel source"),
    # Redstone & Tech
    ("Automatic Item Sorter", "Redstone & Tech", "Sorting system for shared storage"),
    ("Hidden Piston Door", "Redstone & Tech", "Secret entrance to base or vault"),
    ("Item Elevator", "Redstone & Tech", "Vertical transport via water or bubble columns"),
    ("Flying Machine", "Redstone & Tech", "Fast terraforming or transport"),
    ("Redstone Lighting Clock", "Redstone & Tech", "Auto day/night lights around base"),
    ("Minecart Station Hub", "Redstone & Tech", "Rail network connecting bases"),
    # Aesthetic & Decoration
    ("Themed Build: Medieval Village", "Aesthetic & Decoration", "Classic medieval town with market, inn, and walls"),
    ("Themed Build: Japanese Garden", "Aesthetic & Decoration", "Koi pond, torii gate, cherry blossom trees"),
    ("Treehouse Build", "Aesthetic & Decoration", "Multi-level treehouse in a large jungle tree"),
    ("Lighthouse on the Coast", "Aesthetic & Decoration", "Tall coastal beacon with a keeper's cottage"),
    ("Sky Bridge Connecting Bases", "Aesthetic & Decoration", "Decorated elevated walkway between builds"),
    ("Biome Terraforming Project", "Aesthetic & Decoration", "Transform a biome for a custom landscape"),
    ("Pixel Art / Statue Build", "Aesthetic & Decoration", "Large-scale flat or 3D pixel artwork"),
    # Infrastructure & Travel
    ("Nether Highway", "Infrastructure & Travel", "Fast nether route between all bases"),
    ("End Portal Room", "Infrastructure & Travel", "A proper decorated build around the end portal"),
    ("Rail Network", "Infrastructure & Travel", "Connects all member bases via minecart"),
    ("Boat Canal System", "Infrastructure & Travel", "Waterway shortcuts across the map"),
    ("Central Market/Shop Hub", "Infrastructure & Travel", "Trading post for realm-wide commerce"),
    # Defense & Utility
    ("Mob-Proof Perimeter Walls & Lighting", "Defense & Utility", "Keep mobs out of the base area"),
    ("Watchtower", "Defense & Utility", "Tall lookout with spyglass platform"),
    ("Storage Warehouse", "Defense & Utility", "Organized bulk storage for the whole realm"),
    ("Enchanting Room", "Defense & Utility", "Max-level enchanting setup with bookshelves"),
    ("Potion Brewing Station", "Defense & Utility", "Full brewing setup with ingredient storage"),
]

FRIEND_SEED = ["Will", "Alex", "Sam", "Jordan"]


def seed_database():
    if Friend.query.count() == 0:
        for name in FRIEND_SEED:
            db.session.add(Friend(name=name))
    if Idea.query.count() == 0:
        for title, category, description in IDEA_SEED:
            db.session.add(Idea(title=title, category=category, description=description))
    if BaseInfo.query.count() == 0:
        db.session.add(BaseInfo(seed=""))
    db.session.commit()


def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-please-change-in-prod")

    database_url = os.environ.get("DATABASE_URL", "sqlite:///realm.db")
    # Render / Heroku ship "postgres://" but SQLAlchemy 1.4+ requires "postgresql://"
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    with app.app_context():
        db.create_all()
        seed_database()

    # -----------------------------------------------------------------------
    # Auth helpers
    # -----------------------------------------------------------------------

    SITE_PASSWORD = os.environ.get("SITE_PASSWORD", "minecraft")

    def login_required(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not session.get("authenticated"):
                return redirect(url_for("login", next=request.path))
            return f(*args, **kwargs)
        return decorated

    # -----------------------------------------------------------------------
    # Context processors
    # -----------------------------------------------------------------------

    @app.context_processor
    def utility_processor():
        def get_assigned_ids(project):
            return {a.friend_id for a in project.assignments}

        def get_voted_ids(project):
            return {v.friend_id for v in project.votes}

        return dict(get_assigned_ids=get_assigned_ids, get_voted_ids=get_voted_ids)

    # -----------------------------------------------------------------------
    # Auth routes
    # -----------------------------------------------------------------------

    @app.route("/login", methods=["GET", "POST"])
    def login():
        error = None
        if request.method == "POST":
            if request.form.get("password") == SITE_PASSWORD:
                session["authenticated"] = True
                next_url = request.args.get("next") or url_for("board")
                return redirect(next_url)
            error = "Wrong password — try again."
        return render_template("login.html", error=error)

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/")
    @login_required
    def index():
        return redirect(url_for("board"))

    # -----------------------------------------------------------------------
    # Base Info
    # -----------------------------------------------------------------------

    @app.route("/base-info")
    @login_required
    def base_info():
        info = BaseInfo.query.first()
        locations = Location.query.all()
        return render_template("base_info.html", info=info, locations=locations)

    @app.route("/base-info/update", methods=["POST"])
    @login_required
    def update_base_info():
        info = BaseInfo.query.first()
        info.seed = request.form.get("seed", "")
        db.session.commit()
        return redirect(url_for("base_info"))

    @app.route("/base-info/location/add", methods=["POST"])
    @login_required
    def add_location():
        try:
            x = int(request.form.get("x", 0))
            y = int(request.form.get("y", 64))
            z = int(request.form.get("z", 0))
        except ValueError:
            x, y, z = 0, 64, 0
        loc = Location(
            name=request.form.get("name", "Unnamed"),
            x=x, y=y, z=z,
            note=request.form.get("note", ""),
        )
        db.session.add(loc)
        db.session.commit()
        return redirect(url_for("base_info"))

    @app.route("/base-info/location/<int:loc_id>/delete", methods=["POST"])
    @login_required
    def delete_location(loc_id):
        loc = Location.query.get(loc_id)
        if loc:
            db.session.delete(loc)
            db.session.commit()
        return redirect(url_for("base_info"))

    # -----------------------------------------------------------------------
    # Ideas
    # -----------------------------------------------------------------------

    @app.route("/ideas")
    @login_required
    def ideas():
        category_filter = request.args.get("category", "All")
        all_categories = [
            c[0]
            for c in db.session.query(Idea.category)
            .distinct()
            .order_by(Idea.category)
            .all()
        ]

        if category_filter and category_filter != "All":
            idea_list = (
                Idea.query.filter_by(category=category_filter)
                .order_by(Idea.title)
                .all()
            )
        else:
            idea_list = Idea.query.order_by(Idea.category, Idea.title).all()

        grouped = {}
        for idea in idea_list:
            grouped.setdefault(idea.category, []).append(idea)

        friends = Friend.query.order_by(Friend.name).all()

        if request.headers.get("HX-Request"):
            return render_template(
                "partials/ideas_grid.html",
                grouped=grouped,
                category_filter=category_filter,
                friends=friends,
            )
        return render_template(
            "ideas.html",
            grouped=grouped,
            all_categories=all_categories,
            category_filter=category_filter,
            friends=friends,
        )

    @app.route("/ideas/generate", methods=["POST"])
    @login_required
    def generate_ideas():
        category_hint = request.form.get("category", "").strip()
        existing_titles = [i.title for i in Idea.query.with_entities(Idea.title).all()]

        CATEGORIES = [
            "Farms", "Redstone & Tech", "Aesthetic & Decoration",
            "Infrastructure & Travel", "Defense & Utility",
        ]
        category_line = (
            f'Focus on the "{category_hint}" category.'
            if category_hint and category_hint != "All"
            else f"Pick freely from these categories: {', '.join(CATEGORIES)}."
        )

        prompt = f"""You are helping a group of friends brainstorm Minecraft build ideas for their shared realm.
Generate exactly 5 creative, specific build ideas. {category_line}

Avoid these already-existing ideas: {', '.join(existing_titles[:40])}.

Respond with a JSON array of exactly 5 objects. Each object must have these keys:
- "title": short name (3-6 words)
- "category": one of {json.dumps(CATEGORIES)}
- "description": one sentence describing the build and why it's useful or fun

Respond with ONLY the JSON array, no markdown, no explanation."""

        try:
            client = anthropic.Anthropic(
                api_key=os.environ.get("ANTHROPIC_API_KEY")
            )
            message = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text.strip()
            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            ideas = json.loads(raw)
            # Validate structure
            ideas = [
                i for i in ideas
                if isinstance(i, dict) and "title" in i and "category" in i
            ][:5]
        except Exception as e:
            ideas = []
            error = str(e)
            return render_template(
                "partials/generated_ideas.html", ideas=ideas, error=error
            )

        return render_template(
            "partials/generated_ideas.html", ideas=ideas, error=None
        )

    # -----------------------------------------------------------------------
    # Proposals
    # -----------------------------------------------------------------------

    @app.route("/proposals")
    @login_required
    def proposals():
        project_list = (
            Project.query.filter_by(is_on_board=False)
            .order_by(Project.created_at.desc())
            .all()
        )
        friends = Friend.query.order_by(Friend.name).all()
        all_categories = [
            c[0]
            for c in db.session.query(Idea.category)
            .distinct()
            .order_by(Idea.category)
            .all()
        ]
        return render_template(
            "proposals.html",
            projects=project_list,
            friends=friends,
            all_categories=all_categories,
        )

    @app.route("/proposals/new", methods=["GET", "POST"])
    @login_required
    def new_proposal():
        friends = Friend.query.order_by(Friend.name).all()
        all_categories = [
            c[0]
            for c in db.session.query(Idea.category)
            .distinct()
            .order_by(Idea.category)
            .all()
        ]

        if request.method == "POST":
            proposed_by_id = request.form.get("proposed_by_id") or None
            if proposed_by_id:
                proposed_by_id = int(proposed_by_id)
            project = Project(
                title=request.form.get("title", "").strip(),
                category=request.form.get("category", ""),
                description=request.form.get("description", ""),
                proposed_by_id=proposed_by_id,
                is_on_board=False,
            )
            db.session.add(project)
            db.session.commit()
            return redirect(url_for("proposals"))

        return render_template(
            "proposal_form.html",
            friends=friends,
            all_categories=all_categories,
            prefill_title=request.args.get("title", ""),
            prefill_category=request.args.get("category", ""),
            project=None,
        )

    @app.route("/proposals/<int:project_id>/edit", methods=["GET", "POST"])
    @login_required
    def edit_proposal(project_id):
        project = Project.query.get(project_id)
        if not project or project.is_on_board:
            abort(404)
        friends = Friend.query.order_by(Friend.name).all()
        all_categories = [
            c[0]
            for c in db.session.query(Idea.category)
            .distinct()
            .order_by(Idea.category)
            .all()
        ]

        if request.method == "POST":
            project.title = request.form.get("title", project.title).strip()
            project.category = request.form.get("category", project.category)
            project.description = request.form.get("description", project.description)
            proposed_by_id = request.form.get("proposed_by_id") or None
            project.proposed_by_id = int(proposed_by_id) if proposed_by_id else None
            db.session.commit()
            return redirect(url_for("proposals"))

        return render_template(
            "proposal_form.html",
            friends=friends,
            all_categories=all_categories,
            prefill_title=project.title,
            prefill_category=project.category,
            project=project,
        )

    @app.route("/proposals/<int:project_id>/vote", methods=["POST"])
    @login_required
    def vote_proposal(project_id):
        project = Project.query.get(project_id)
        if not project:
            abort(404)
        try:
            friend_id = int(request.form.get("friend_id", 0))
        except (ValueError, TypeError):
            abort(400)

        existing = Vote.query.filter_by(
            project_id=project_id, friend_id=friend_id
        ).first()
        if existing:
            db.session.delete(existing)
        else:
            db.session.add(Vote(project_id=project_id, friend_id=friend_id))
        db.session.commit()

        friends = Friend.query.order_by(Friend.name).all()
        voted_ids = {v.friend_id for v in project.votes}
        return render_template(
            "partials/vote_section.html",
            project=project,
            friends=friends,
            voted_ids=voted_ids,
        )

    @app.route("/proposals/<int:project_id>/promote", methods=["POST"])
    @login_required
    def promote_proposal(project_id):
        project = Project.query.get(project_id)
        if not project:
            abort(404)
        project.is_on_board = True
        project.status = "not_started"
        project.updated_at = datetime.utcnow()
        db.session.commit()
        return redirect(url_for("board"))

    @app.route("/proposals/<int:project_id>/delete", methods=["POST"])
    @login_required
    def delete_proposal(project_id):
        project = Project.query.get(project_id)
        if project:
            db.session.delete(project)
            db.session.commit()
        return redirect(url_for("proposals"))

    # -----------------------------------------------------------------------
    # Board
    # -----------------------------------------------------------------------

    @app.route("/board")
    @login_required
    def board():
        status_filter = request.args.get("status", "")
        category_filter = request.args.get("category", "")
        assigned_filter = request.args.get("assigned", "")

        query = Project.query.filter_by(is_on_board=True)
        if status_filter:
            query = query.filter_by(status=status_filter)
        if category_filter:
            query = query.filter_by(category=category_filter)
        if assigned_filter:
            try:
                af_id = int(assigned_filter)
                sub = (
                    db.session.query(ProjectAssignment.project_id)
                    .filter_by(friend_id=af_id)
                    .subquery()
                )
                query = query.filter(Project.id.in_(sub))
            except (ValueError, TypeError):
                pass

        STATUS_ORDER = {"in_progress": 0, "not_started": 1, "done": 2}
        projects = query.all()
        projects.sort(
            key=lambda p: (
                STATUS_ORDER.get(p.status, 3),
                -(p.updated_at or datetime.min).timestamp(),
            )
        )

        friends = Friend.query.order_by(Friend.name).all()
        board_categories = [
            c[0]
            for c in db.session.query(Project.category)
            .filter(Project.is_on_board == True, Project.category != "")
            .distinct()
            .order_by(Project.category)
            .all()
        ]

        if request.headers.get("HX-Request"):
            return render_template(
                "partials/board_cards.html", projects=projects, friends=friends
            )

        return render_template(
            "board.html",
            projects=projects,
            friends=friends,
            board_categories=board_categories,
            status_filter=status_filter,
            category_filter=category_filter,
            assigned_filter=assigned_filter,
        )

    @app.route("/board/new", methods=["GET", "POST"])
    @login_required
    def new_board_project():
        friends = Friend.query.order_by(Friend.name).all()
        all_categories = [
            c[0]
            for c in db.session.query(Idea.category)
            .distinct()
            .order_by(Idea.category)
            .all()
        ]

        if request.method == "POST":
            project = Project(
                title=request.form.get("title", "").strip(),
                category=request.form.get("category", ""),
                description=request.form.get("description", ""),
                image_url=request.form.get("image_url", ""),
                is_on_board=True,
                status="not_started",
            )
            db.session.add(project)
            db.session.flush()

            for line in request.form.get("materials", "").splitlines():
                line = line.strip()
                if line:
                    db.session.add(MaterialItem(project_id=project.id, text=line))

            for fid in request.form.getlist("assigned_friends"):
                try:
                    db.session.add(
                        ProjectAssignment(project_id=project.id, friend_id=int(fid))
                    )
                except (ValueError, TypeError):
                    pass

            db.session.commit()
            return redirect(url_for("board"))

        return render_template(
            "project_form.html",
            project=None,
            friends=friends,
            all_categories=all_categories,
            current_materials="",
            assigned_friend_ids=set(),
        )

    @app.route("/board/<int:project_id>/edit", methods=["GET", "POST"])
    @login_required
    def edit_board_project(project_id):
        project = Project.query.get(project_id)
        if not project or not project.is_on_board:
            abort(404)
        friends = Friend.query.order_by(Friend.name).all()
        all_categories = [
            c[0]
            for c in db.session.query(Idea.category)
            .distinct()
            .order_by(Idea.category)
            .all()
        ]

        if request.method == "POST":
            project.title = request.form.get("title", project.title).strip()
            project.category = request.form.get("category", project.category)
            project.description = request.form.get("description", project.description)
            project.image_url = request.form.get("image_url", "")
            project.updated_at = datetime.utcnow()

            MaterialItem.query.filter_by(project_id=project_id).delete()
            for line in request.form.get("materials", "").splitlines():
                line = line.strip()
                if line:
                    db.session.add(MaterialItem(project_id=project_id, text=line))

            ProjectAssignment.query.filter_by(project_id=project_id).delete()
            for fid in request.form.getlist("assigned_friends"):
                try:
                    db.session.add(
                        ProjectAssignment(project_id=project_id, friend_id=int(fid))
                    )
                except (ValueError, TypeError):
                    pass

            db.session.commit()
            return redirect(url_for("board"))

        current_materials = "\n".join(m.text for m in project.materials)
        assigned_friend_ids = {a.friend_id for a in project.assignments}
        return render_template(
            "project_form.html",
            project=project,
            friends=friends,
            all_categories=all_categories,
            current_materials=current_materials,
            assigned_friend_ids=assigned_friend_ids,
        )

    @app.route("/board/<int:project_id>/status", methods=["POST"])
    @login_required
    def update_status(project_id):
        project = Project.query.get(project_id)
        if not project:
            abort(404)
        new_status = request.form.get("status", "not_started")
        if new_status in ("not_started", "in_progress", "done"):
            project.status = new_status
            project.updated_at = datetime.utcnow()
            db.session.commit()
        return render_template("partials/status_select.html", project=project)

    @app.route(
        "/board/<int:project_id>/material/<int:item_id>/toggle", methods=["POST"]
    )
    @login_required
    def toggle_material(project_id, item_id):
        item = MaterialItem.query.get(item_id)
        if not item or item.project_id != project_id:
            abort(404)
        item.gathered = not item.gathered
        db.session.commit()
        return render_template(
            "partials/material_item.html", item=item, project_id=project_id
        )

    @app.route("/board/<int:project_id>/assign", methods=["POST"])
    @login_required
    def update_assignments(project_id):
        project = Project.query.get(project_id)
        if not project:
            abort(404)
        ProjectAssignment.query.filter_by(project_id=project_id).delete()
        for fid in request.form.getlist("friend_ids"):
            try:
                db.session.add(
                    ProjectAssignment(project_id=project_id, friend_id=int(fid))
                )
            except (ValueError, TypeError):
                pass
        db.session.commit()
        friends = Friend.query.order_by(Friend.name).all()
        assigned_ids = {a.friend_id for a in project.assignments}
        return render_template(
            "partials/assignment_section.html",
            project=project,
            friends=friends,
            assigned_ids=assigned_ids,
        )

    @app.route("/board/<int:project_id>/delete", methods=["POST"])
    @login_required
    def delete_board_project(project_id):
        project = Project.query.get(project_id)
        if project:
            db.session.delete(project)
            db.session.commit()
        return redirect(url_for("board"))

    # -----------------------------------------------------------------------
    # Settings
    # -----------------------------------------------------------------------

    @app.route("/settings")
    @login_required
    def settings():
        friends = Friend.query.order_by(Friend.name).all()
        info = BaseInfo.query.first()
        locations = Location.query.all()
        return render_template(
            "settings.html", friends=friends, info=info, locations=locations
        )

    @app.route("/settings/friends/add", methods=["POST"])
    @login_required
    def add_friend():
        name = request.form.get("name", "").strip()
        if name and not Friend.query.filter_by(name=name).first():
            db.session.add(Friend(name=name))
            db.session.commit()
        return redirect(url_for("settings"))

    @app.route("/settings/friends/<int:friend_id>/rename", methods=["POST"])
    @login_required
    def rename_friend(friend_id):
        friend = Friend.query.get(friend_id)
        if friend:
            new_name = request.form.get("name", "").strip()
            if new_name and not Friend.query.filter_by(name=new_name).first():
                friend.name = new_name
                db.session.commit()
        return redirect(url_for("settings"))

    @app.route("/settings/friends/<int:friend_id>/delete", methods=["POST"])
    @login_required
    def delete_friend(friend_id):
        friend = Friend.query.get(friend_id)
        if friend:
            db.session.delete(friend)
            db.session.commit()
        return redirect(url_for("settings"))

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
