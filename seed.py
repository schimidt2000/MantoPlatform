from app import create_app, db
from app.models import User, Role, Permission

def get_or_create_role(name: str) -> Role:
    role = Role.query.filter_by(name=name).first()
    if not role:
        role = Role(name=name)
        db.session.add(role)
    return role

def get_or_create_perm(code: str) -> Permission:
    perm = Permission.query.filter_by(code=code).first()
    if not perm:
        perm = Permission(code=code)
        db.session.add(perm)
    return perm

def main():
    app = create_app()
    with app.app_context():
        # Permissões base
        p_user_manage = get_or_create_perm("user.manage")
        p_rh_view = get_or_create_perm("rh.view")

        # Roles base
        superadmin = get_or_create_role("SUPERADMIN")
        rh = get_or_create_role("RH")

        # SUPERADMIN pode tudo (mas ainda adicionamos a perm p/ consistência)
        if p_user_manage not in superadmin.permissions:
            superadmin.permissions.append(p_user_manage)

        if p_rh_view not in rh.permissions:
            rh.permissions.append(p_rh_view)

        # Seu usuário SUPERADMIN (ajuste nome/email se quiser)
        email = "admin@manto.local"
        user = User.query.filter_by(email=email).first()

        if not user:
            user = User(email=email, name="SuperAdmin", is_active=True, must_change_password=False)
            user.set_password("admin123")
            db.session.add(user)

        # Garantir que SÓ você tem SUPERADMIN
        # 1) Remove SUPERADMIN de qualquer outro usuário
        all_users = User.query.all()
        for u in all_users:
            u.roles = [r for r in u.roles if r.name != "SUPERADMIN"]

        # 2) Adiciona SUPERADMIN somente ao seu user
        if superadmin not in user.roles:
            user.roles.append(superadmin)

        db.session.commit()
        print("Seed OK: SUPERADMIN garantido apenas para", email)

if __name__ == "__main__":
    main()
