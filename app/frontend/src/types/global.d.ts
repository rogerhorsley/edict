interface Window {
  google?: {
    accounts: {
      id: {
        initialize: (config: {
          client_id: string;
          callback: (response: { credential: string; select_by: string }) => void;
        }) => void;
        renderButton: (
          element: HTMLElement,
          config: {
            type?: string;
            size?: string;
            theme?: string;
            text?: string;
            width?: number;
          },
        ) => void;
        prompt: () => void;
      };
    };
  };
}
