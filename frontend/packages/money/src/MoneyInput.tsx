import { forwardRef, useCallback, type ChangeEvent, type InputHTMLAttributes } from "react";
import { formatBRL } from "./formatBRL";
import { digitsToNumber } from "./parseBRL";

type NativeInputProps = Omit<
  InputHTMLAttributes<HTMLInputElement>,
  "value" | "onChange" | "type" | "inputMode"
>;

export interface MoneyInputProps extends NativeInputProps {
  /** Valor numérico "cru" (o que vai no corpo JSON). */
  value: number;
  /** Chamado com o novo valor numérico a cada digitação. */
  onValueChange: (value: number) => void;
}

/**
 * Campo de entrada monetária brasileira — fonte única de máscara no frontend (FR-012).
 *
 * Exibe o valor sempre formatado ("1.234,56") enquanto guarda/emite o número puro. O usuário
 * digita apenas os dígitos; os dois últimos viram os centavos automaticamente.
 */
export const MoneyInput = forwardRef<HTMLInputElement, MoneyInputProps>(
  function MoneyInput({ value, onValueChange, ...rest }, ref) {
    const handleChange = useCallback(
      (event: ChangeEvent<HTMLInputElement>) => {
        onValueChange(digitsToNumber(event.target.value));
      },
      [onValueChange],
    );

    return (
      <input
        {...rest}
        ref={ref}
        type="text"
        inputMode="numeric"
        value={formatBRL(value)}
        onChange={handleChange}
      />
    );
  },
);
