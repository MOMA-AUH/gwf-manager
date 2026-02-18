try:
    from gwf import AnonymousTarget, Workflow
except ImportError:

    class AnonymousTarget:
        pass

    class Workflow:
        pass
