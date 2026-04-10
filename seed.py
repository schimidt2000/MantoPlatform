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

        # Remover roles obsoletas do banco
        for obsolete in ("ADMIN", "RH", "VENDAS"):
            role = Role.query.filter_by(name=obsolete).first()
            if role:
                db.session.delete(role)
        db.session.flush()

        # Roles do sistema
        superadmin = get_or_create_role("SUPERADMIN")
        get_or_create_role("CASTING")
        get_or_create_role("FIGURINO")
        get_or_create_role("COMERCIAL")
        get_or_create_role("FINANCEIRO")
        get_or_create_role("ENSAIO")

        if p_user_manage not in superadmin.permissions:
            superadmin.permissions.append(p_user_manage)

        TARGET_EMAIL = "joao@mantoproducoes.com.br"

        # Só cria superadmin na primeira execução (banco vazio)
        if User.query.count() == 0:
            user = User(
                email=TARGET_EMAIL,
                name="João Pedro Schimidt Mantovani",
                is_active=True,
                must_change_password=False,
            )
            user.set_password("$ch!m1dT@9")
            user.roles = [superadmin]
            db.session.add(user)
            print(f"Seed OK: usuário inicial criado ({TARGET_EMAIL})")
        else:
            print("Seed OK: usuários já existem, nenhuma alteração.")

        db.session.commit()

if __name__ == "__main__":
    main()
