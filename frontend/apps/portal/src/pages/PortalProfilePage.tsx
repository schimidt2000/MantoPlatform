import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { ApiRequestError, assetUrl } from "@manto/api-client";
import { Button, Card, CardContent, CardHeader, CardTitle, FileUpload, Skeleton } from "@manto/ui";
import { ExternalLink, Trash2 } from "lucide-react";
import { FormError, FormField, FormSuccess } from "../components/FormField";
import {
  useAddPortfolioLink,
  useAddPortfolioPhoto,
  useDeletePortfolioItem,
  useProfile,
  useUpdateProfile,
  type PortalProfile,
  type PortalProfilePatch,
} from "../lib/portalProfile";

const PHOTO_ACCEPT = "image/jpeg,image/png,image/webp";
const PHOTO_MAX = 8 * 1024 * 1024;

/** Campos do formulário — strings, porque `<input>` sempre devolve string. */
interface ProfileForm {
  full_name: string;
  artistic_name: string;
  phone: string;
  email_contact: string;
  height_cm: string;
  clothing_size_top: string;
  clothing_size_bottom: string;
  shoe_size: string;
  pix_key: string;
  pix_key_type: string;
}

function toFormValues(profile: PortalProfile): ProfileForm {
  return {
    full_name: profile.full_name ?? "",
    artistic_name: profile.artistic_name ?? "",
    phone: profile.phone ?? "",
    email_contact: profile.email_contact ?? "",
    height_cm: profile.height_cm != null ? String(profile.height_cm) : "",
    clothing_size_top: profile.clothing_size_top ?? "",
    clothing_size_bottom: profile.clothing_size_bottom ?? "",
    shoe_size: profile.shoe_size ?? "",
    pix_key: profile.pix_key ?? "",
    pix_key_type: profile.pix_key_type ?? "",
  };
}

function toPatch(values: ProfileForm): PortalProfilePatch {
  return {
    ...values,
    // O backend aceita `null` para limpar e número para gravar — string vazia vira `null`.
    height_cm: values.height_cm.trim() === "" ? null : Number(values.height_cm),
  };
}

function MedidasSection({
  register,
  errors,
}: {
  register: ReturnType<typeof useForm<ProfileForm>>["register"];
  errors: Partial<Record<keyof ProfileForm, { message?: string }>>;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Medidas corporais</CardTitle>
        <p className="text-sm text-muted">
          Usadas pela equipe de figurino para separar as peças do seu personagem.
        </p>
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-3">
        <FormField
          label="Altura (cm)"
          type="number"
          inputMode="numeric"
          min={50}
          max={260}
          placeholder="170"
          error={errors.height_cm?.message}
          {...register("height_cm")}
        />
        <FormField
          label="Calçado"
          type="text"
          inputMode="numeric"
          placeholder="40"
          error={errors.shoe_size?.message}
          {...register("shoe_size")}
        />
        <FormField
          label="Tamanho (cima)"
          type="text"
          placeholder="M"
          error={errors.clothing_size_top?.message}
          {...register("clothing_size_top")}
        />
        <FormField
          label="Tamanho (baixo)"
          type="text"
          placeholder="42"
          error={errors.clothing_size_bottom?.message}
          {...register("clothing_size_bottom")}
        />
      </CardContent>
    </Card>
  );
}

function PortfolioSection({ profile }: { profile: PortalProfile }) {
  const addPhoto = useAddPortfolioPhoto();
  const addLink = useAddPortfolioLink();
  const deleteItem = useDeletePortfolioItem();

  const [linkUrl, setLinkUrl] = useState("");
  const [linkLabel, setLinkLabel] = useState("");
  const [photoError, setPhotoError] = useState<string | undefined>();
  const [linkError, setLinkError] = useState<string | null>(null);

  const photos = profile.media.filter((item) => item.media_type === "photo");
  const links = profile.media.filter((item) => item.media_type === "link");
  const photoSlotsLeft = profile.max_photos - photos.length;

  function handleAddLink() {
    setLinkError(null);
    addLink.mutate(
      { url: linkUrl, label: linkLabel || undefined },
      {
        onSuccess: () => {
          setLinkUrl("");
          setLinkLabel("");
        },
        onError: (error) => setLinkError(error.message),
      },
    );
  }

  function handleDelete(mediaId: number, description: string) {
    if (!window.confirm(`Remover ${description}? Esta ação não pode ser desfeita.`)) return;
    deleteItem.mutate(mediaId);
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Portfólio</CardTitle>
        <p className="text-sm text-muted">
          Até {profile.max_photos} fotos de atuação e quantos links quiser (Vimeo, YouTube…).
        </p>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-ink">
            Fotos de atuação ({photos.length}/{profile.max_photos})
          </h3>

          {photos.length > 0 && (
            <ul className="grid grid-cols-3 gap-2">
              {photos.map((item) => (
                <li key={item.id} className="relative">
                  <img
                    src={assetUrl(item.file_url)}
                    alt={item.label || "Foto de atuação"}
                    className="aspect-square w-full rounded-md object-cover"
                  />
                  <button
                    type="button"
                    aria-label={`Remover ${item.label || "foto de atuação"}`}
                    onClick={() => handleDelete(item.id, item.label || "esta foto")}
                    disabled={deleteItem.isPending}
                    className="absolute right-1 top-1 flex h-9 w-9 items-center justify-center rounded-full bg-panel/90 text-red shadow-sm disabled:opacity-50"
                  >
                    <Trash2 className="h-4 w-4" aria-hidden="true" />
                  </button>
                </li>
              ))}
            </ul>
          )}

          {photoSlotsLeft > 0 ? (
            <FileUpload
              label="Adicionar foto de atuação"
              accept={PHOTO_ACCEPT}
              maxSizeBytes={PHOTO_MAX}
              error={photoError}
              onChange={(file) => {
                setPhotoError(undefined);
                if (!file) return;
                addPhoto.mutate(
                  { file },
                  {
                    onError: (error) =>
                      setPhotoError(
                        error instanceof ApiRequestError ? error.message : "Falha no envio.",
                      ),
                  },
                );
              }}
            />
          ) : (
            <p className="text-xs text-muted">
              Limite de fotos atingido. Remova uma para adicionar outra.
            </p>
          )}
          {addPhoto.isPending && <p className="text-xs text-muted">Enviando foto…</p>}
        </div>

        <div className="space-y-3 border-t border-line pt-4">
          <h3 className="text-sm font-semibold text-ink">Links ({links.length})</h3>

          {links.length > 0 && (
            <ul className="space-y-2">
              {links.map((item) => (
                <li
                  key={item.id}
                  className="flex items-center justify-between gap-2 rounded-md border border-line px-3 py-2"
                >
                  <a
                    href={item.url ?? "#"}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex min-h-[44px] min-w-0 flex-1 items-center gap-2 text-sm text-accent hover:underline"
                  >
                    <ExternalLink className="h-4 w-4 shrink-0" aria-hidden="true" />
                    <span className="truncate">{item.label || item.url}</span>
                  </a>
                  <button
                    type="button"
                    aria-label={`Remover ${item.label || "link"}`}
                    onClick={() => handleDelete(item.id, item.label || "este link")}
                    disabled={deleteItem.isPending}
                    className="flex h-11 w-11 shrink-0 items-center justify-center rounded-md text-red disabled:opacity-50"
                  >
                    <Trash2 className="h-4 w-4" aria-hidden="true" />
                  </button>
                </li>
              ))}
            </ul>
          )}

          <div className="space-y-2">
            <FormField
              label="Endereço do link"
              name="portfolio_url"
              type="url"
              inputMode="url"
              placeholder="https://vimeo.com/..."
              value={linkUrl}
              onChange={(event) => setLinkUrl(event.target.value)}
            />
            <FormField
              label="Descrição (opcional)"
              name="portfolio_label"
              type="text"
              placeholder="Demo reel 2026"
              value={linkLabel}
              onChange={(event) => setLinkLabel(event.target.value)}
            />
            <FormError>{linkError}</FormError>
            <Button
              type="button"
              variant="outline"
              className="w-full"
              disabled={!linkUrl.trim()}
              loading={addLink.isPending}
              onClick={handleAddLink}
            >
              Adicionar link
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

/** Perfil e portfólio do talento: dados pessoais, medidas corporais, PIX, fotos e links. */
export function PortalProfilePage() {
  const profileQuery = useProfile();
  const updateProfile = useUpdateProfile();
  const [formError, setFormError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors, isDirty },
  } = useForm<ProfileForm>();

  // O formulário nasce vazio e é preenchido quando o perfil chega — `values` do RHF sobrescreve
  // o que o usuário digitou a cada refetch, então o preenchimento é feito uma vez, por `reset`.
  useEffect(() => {
    if (profileQuery.data) reset(toFormValues(profileQuery.data));
  }, [profileQuery.data, reset]);

  const onSubmit = handleSubmit((values) => {
    setFormError(null);
    setSaved(false);
    updateProfile.mutate(toPatch(values), {
      onSuccess: (profile) => {
        reset(toFormValues(profile));
        setSaved(true);
      },
      onError: (error) => {
        if (error instanceof ApiRequestError && error.fields) {
          for (const [field, message] of Object.entries(error.fields)) {
            setError(field as keyof ProfileForm, { message });
          }
          return;
        }
        setFormError(error.message);
      },
    });
  });

  if (profileQuery.isLoading) {
    return (
      <div className="space-y-3 p-4">
        <Skeleton className="h-8 w-40" />
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  if (profileQuery.isError || !profileQuery.data) {
    return (
      <div className="p-4">
        <FormError>Não foi possível carregar seu perfil. Tente novamente.</FormError>
        <Button className="mt-3 w-full" onClick={() => profileQuery.refetch()}>
          Recarregar
        </Button>
      </div>
    );
  }

  const profile = profileQuery.data;

  return (
    <div className="space-y-4 p-4">
      <h1 className="text-lg font-semibold text-ink">Meu perfil</h1>

      <form onSubmit={onSubmit} noValidate className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle>Dados pessoais</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <FormField
              label="Nome completo"
              type="text"
              autoComplete="name"
              error={errors.full_name?.message}
              {...register("full_name")}
            />
            <FormField
              label="Nome artístico"
              type="text"
              error={errors.artistic_name?.message}
              {...register("artistic_name")}
            />
            <FormField
              label="Telefone"
              type="tel"
              inputMode="tel"
              autoComplete="tel"
              error={errors.phone?.message}
              {...register("phone")}
            />
            <FormField
              label="E-mail"
              type="email"
              inputMode="email"
              autoComplete="email"
              error={errors.email_contact?.message}
              {...register("email_contact")}
            />
          </CardContent>
        </Card>

        <MedidasSection register={register} errors={errors} />

        <Card>
          <CardHeader>
            <CardTitle>Pagamento</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <FormField
              label="Chave PIX"
              type="text"
              error={errors.pix_key?.message}
              {...register("pix_key")}
            />
            <FormField
              label="Tipo da chave"
              type="text"
              placeholder="CPF, e-mail, telefone, aleatória"
              error={errors.pix_key_type?.message}
              {...register("pix_key_type")}
            />
          </CardContent>
        </Card>

        <FormError>{formError}</FormError>
        {saved && !isDirty && <FormSuccess>Perfil atualizado com sucesso.</FormSuccess>}

        <Button type="submit" loading={updateProfile.isPending} className="w-full">
          Salvar alterações
        </Button>
      </form>

      <PortfolioSection profile={profile} />
    </div>
  );
}
