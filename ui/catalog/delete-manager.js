/**
 * DeleteManager - Gerenciador centralizado de operações de exclusão
 * Reutilizável em diferentes contextos (site, model, duplicates, etc)
 */

class DeleteManager {
  /**
   * @param {Object} config - Configuração da operação de delete
   * @param {string} config.endpoint - URL do endpoint (ex: /api/delete_model)
   * @param {string} config.confirmMessage - Mensagem de confirmação
   * @param {Object} config.data - Dados a enviar na requisição
   * @param {Function} config.onSuccess - Callback executado se sucesso
   * @param {Function} config.onError - Callback executado se erro
   * @param {HTMLElement} config.element - Elemento a remover do DOM (opcional)
   * @param {boolean} config.showNotification - Mostrar notificação (padrão: true)
   * @param {boolean} config.suppressConfirmation - Suprimir confirmação modal (padrão: false)
   * @param {string} config.successMessage - Mensagem de sucesso
   * @param {string} config.errorMessage - Mensagem de erro
   */
  constructor(config) {
    this.endpoint = config.endpoint;
    this.confirmMessage = config.confirmMessage;
    this.data = config.data;
    this.onSuccess = config.onSuccess || (() => {});
    this.onError = config.onError || (() => {});
    this.element = config.element;
    this.showNotification = config.showNotification !== false;
    this.suppressConfirmation = config.suppressConfirmation || false;
    this.successMessage = config.successMessage || "✅ Deletado com sucesso";
    this.errorMessage = config.errorMessage || "❌ Erro ao deletar";
    this.isDeleting = false;
  }

  /**
   * Executa a operação de delete com confirmação
   * @returns {Promise<boolean>} Retorna true se sucesso, false caso contrário
   */
  async execute() {
    // Evitar deletar duas vezes
    if (this.isDeleting) {
      console.warn("[DELETE] Operação já em progresso");
      return false;
    }

    // Pedir confirmação usando modal customizado (a menos que esteja suprimida)
    if (!this.suppressConfirmation) {
      const confirmed = await this._showConfirmDialog();
      if (!confirmed) {
        console.log("[DELETE] Operação cancelada pelo usuário");
        return false;
      }
    }

    this.isDeleting = true;

    try {
      console.log(`[DELETE] Iniciando: POST ${this.endpoint}`, this.data);

      const response = await fetch(this.endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(this.data),
      });

      const result = await response.json();
      console.log(`[DELETE] Resposta: ${response.status}`, result);

      if (!response.ok) {
        throw new Error(result.message || result.error || `HTTP ${response.status}`);
      }

      if (!result.status === "deleted" && result.status !== "deleted") {
        throw new Error(result.error || "Operação falhou");
      }

      console.log("[DELETE] ✅ Sucesso");

      // Remover elemento do DOM se fornecido
      if (this.element && this.element.parentNode) {
        this.element.remove();
      }

      // Mostrar notificação
      if (this.showNotification) {
        this._showToast(this.successMessage, "success");
      }

      // Executar callback de sucesso
      this.onSuccess(result);

      return true;
    } catch (error) {
      console.error("[DELETE] ❌ Erro:", error.message);

      // Mostrar notificação de erro
      if (this.showNotification) {
        this._showToast(`${this.errorMessage}: ${error.message}`, "error");
      }

      // Executar callback de erro
      this.onError(error);

      return false;
    } finally {
      this.isDeleting = false;
    }
  }

  /**
   * Deleta múltiplos itens sequencialmente
   * @param {Array<DeleteManager>} managers - Array de instâncias DeleteManager
   * @param {Function} onProgress - Callback de progresso (deletados, total)
   * @returns {Promise<Object>} { successCount, failureCount, errors }
   */
  static async executeBatch(managers, onProgress = null) {
    let successCount = 0;
    let failureCount = 0;
    const errors = [];

    console.log(`[DELETE_BATCH] Iniciando batch de ${managers.length} item(s)`);

    for (let i = 0; i < managers.length; i++) {
      const manager = managers[i];
      const success = await manager.execute();

      if (success) {
        successCount++;
      } else {
        failureCount++;
        errors.push({
          index: i,
          data: manager.data,
          error: "Falha ao deletar",
        });
      }

      if (onProgress) {
        onProgress(successCount + failureCount, managers.length);
      }
    }

    console.log(
      `[DELETE_BATCH] Concluído: ${successCount} sucesso(s), ${failureCount} erro(s)`
    );

    return {
      successCount,
      failureCount,
      errors,
      totalCount: managers.length,
      allSuccess: failureCount === 0,
    };
  }

  /**
   * Deleta múltiplos itens com uma única confirmação
   * @param {Array<DeleteManager>} managers - Array de instâncias DeleteManager
   * @param {string} confirmMessage - Mensagem de confirmação (ex: "Deletar 5 arquivos?")
   * @param {Function} onProgress - Callback de progresso (deletados, total)
   * @returns {Promise<Object>} { successCount, failureCount, errors }
   */
  static async executeBatchWithConfirmation(managers, confirmMessage, onProgress = null) {
    // Mostrar confirmação única
    const temp = new DeleteManager({
      endpoint: "/dummy",
      confirmMessage: confirmMessage,
      data: {}
    });

    const confirmed = await temp._showConfirmDialog();
    if (!confirmed) {
      console.log("[DELETE_BATCH] Operação cancelada pelo usuário");
      return {
        successCount: 0,
        failureCount: managers.length,
        errors: [],
        totalCount: managers.length,
        allSuccess: false,
      };
    }

    // Executar batch sem pedir confirmação individual
    let successCount = 0;
    let failureCount = 0;
    const errors = [];

    console.log(`[DELETE_BATCH] Iniciando batch de ${managers.length} item(s) com confirmação única`);

    for (let i = 0; i < managers.length; i++) {
      const manager = managers[i];
      const success = await manager.execute();

      if (success) {
        successCount++;
      } else {
        failureCount++;
        errors.push({
          index: i,
          data: manager.data,
          error: "Falha ao deletar",
        });
      }

      if (onProgress) {
        onProgress(successCount + failureCount, managers.length);
      }
    }

    console.log(
      `[DELETE_BATCH] Concluído: ${successCount} sucesso(s), ${failureCount} erro(s)`
    );

    return {
      successCount,
      failureCount,
      errors,
      totalCount: managers.length,
      allSuccess: failureCount === 0,
    };
  }

  /**
   * Mostra notificação visual
   * @private
   */
  _showToast(message, type = "info") {
    // Procurar por elemento toast existente
    let toast = document.getElementById("toast");

    if (!toast) {
      // Criar toast se não existir
      toast = document.createElement("div");
      toast.id = "toast";
      toast.className = "toast";
      document.body.appendChild(toast);
    }

    toast.textContent = message;
    toast.className = `toast ${type}`;

    // Definir timeout para remover
    setTimeout(() => {
      toast.classList.remove("show");
    }, 3000);

    // Adicionar classe show com pequeno delay para trigger animação
    setTimeout(() => {
      toast.classList.add("show");
    }, 10);
  }

  /**
   * Mostra modal de confirmação customizado
   * @private
   * @returns {Promise<boolean>} Resolve com true se confirmado, false se cancelado
   */
  _showConfirmDialog() {
    return new Promise((resolve) => {
      // Criar modal
      const modal = document.createElement("div");
      modal.className = "modal";
      modal.id = `confirm-modal-${Date.now()}`;

      modal.innerHTML = `
        <div class="modal-backdrop"></div>
        <div class="modal-content">
          <h2 class="modal-title">⚠️ Confirmar Exclusão</h2>
          <div class="modal-body">
            <p>${this.confirmMessage}</p>
          </div>
          <div class="modal-footer">
            <button class="modal-btn" id="btn-cancel-${Date.now()}">❌ Cancelar</button>
            <button class="modal-btn modal-btn-primary" id="btn-confirm-${Date.now()}">🗑️ Deletar</button>
          </div>
        </div>
      `;

      document.body.appendChild(modal);

      // Agregar classe que remove hidden
      setTimeout(() => modal.classList.remove("hidden"), 10);

      const btnCancel = modal.querySelector(`#btn-cancel-${Date.now()}`);
      const btnConfirm = modal.querySelector(`#btn-confirm-${Date.now()}`);

      const cleanup = () => {
        modal.classList.add("hidden");
        setTimeout(() => modal.remove(), 300); // Aguardar animação
      };

      btnCancel.addEventListener("click", () => {
        cleanup();
        resolve(false);
      });

      btnConfirm.addEventListener("click", () => {
        cleanup();
        resolve(true);
      });

      // Fechar modal ao clicar no backdrop
      const backdrop = modal.querySelector(".modal-backdrop");
      backdrop.addEventListener("click", () => {
        cleanup();
        resolve(false);
      });
    });
  }

  /**
   * Factory para criar DeleteManager para site
   */
  static createModelDelete(site, modelName, element = null, callbacks = {}) {
    return new DeleteManager({
      endpoint: "/api/delete_model",
      confirmMessage: `Excluir a modelo "${modelName}"?`,
      data: { site, model: modelName },
      element,
      successMessage: "✅ Modelo deletada com sucesso",
      errorMessage: "❌ Erro ao deletar modelo",
      ...callbacks,
    });
  }

  /**
   * Factory para criar DeleteManager para arquivo (imagem/vídeo)
   */
  static createFileDelete(site, model, filename, element = null, callbacks = {}) {
    return new DeleteManager({
      endpoint: "/api/delete_file",
      confirmMessage: `Excluir arquivo "${filename}"?`,
      data: { site, model, file: filename },
      element,
      successMessage: "✅ Arquivo deletado com sucesso",
      errorMessage: "❌ Erro ao deletar arquivo",
      ...callbacks,
    });
  }

  /**
   * Factory para criar DeleteManager para arquivo duplicado
   */
  static createDuplicateDelete(filePath, element = null, callbacks = {}) {
    return new DeleteManager({
      endpoint: "/api/delete_duplicate",
      confirmMessage: `Excluir arquivo duplicado?\n${filePath}`,
      data: { path: filePath },
      element,
      successMessage: "✅ Arquivo duplicado deletado",
      errorMessage: "❌ Erro ao deletar arquivo",
      ...callbacks,
    });
  }
}
