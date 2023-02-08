#  __  __           ___                   _
# |  \/  |__ _ _ __| __|__ _ _ _ __  __ _| |_
# | |\/| / _` | '_ \ _/ _ \ '_| '  \/ _` |  _|
# |_|  |_\__,_| .__/_|\___/_| |_|_|_\__,_|\__|
#             |_|
# Map Format
import logging
import uuid
from random import random as pyrandom
from typing import Any, List, Optional, Union

from .validation import Validator


def trunc_float(value: Union[int, float, str], prec=6):
    return round(float(value), prec)


def trunc_float2(value: Union[int, float, str]):
    return trunc_float(value, prec=2)


class LoadMixin():
    load_args = []

    @classmethod
    def load(Cls, data: dict, _validator=Validator(), raise_error=True):
        validator = _validator

        logging.debug(f"{Cls.__name__}.load(): data=`{data}` validator=`{validator}`")  # TODO TEST
        kwargs = {}
        errors = []
        for name, coerce_callable in Cls.load_args:
            value = data.get(name)
            # value is not provided but attribute declared as optional
            was_fixed = False
            logging.debug(f" - check '{name}' of `{coerce_callable.__name__}`")
            if value is None:
                if validator:
                    try:
                        value, was_fixed = validator.clean_attr(name)
                    except Exception as ex:
                        if raise_error:
                            raise ex
                        else:
                            errors.append(ex)
                            continue

                    if not was_fixed:
                        continue  # optional
                else:
                    logging.debug("no validatator, skip")
                    continue

            logging.debug(f" coerce is {type(coerce_callable)}")
            if isinstance(coerce_callable, type) and issubclass(coerce_callable, LoadMixin):
                logging.debug(f"will call argument's '{name}' load()")
                if validator and not was_fixed:
                    sub_validator = validator.get(name, {})
                    arg = coerce_callable.load(value, sub_validator, raise_error=raise_error)
                else:
                    arg = coerce_callable.load(value, raise_error=raise_error)

            elif type(value) == dict:  # strict check, not isinstance()
                arg = coerce_callable(**value)
            else:
                arg = coerce_callable(value)
            name = name.replace(':', '')
            kwargs[name] = arg
            # logging.debug(f" kwarg '{name}': {arg}")

        logging.debug(f"kwargs: {kwargs}")
        if errors:
            logging.error("Validation failed, errors: ")
            for error in errors:
                logging.error(f" - {error}")
            raise ValueError(f"Validation of `{Cls.__name__}` failed!")
        return Cls(**kwargs)

    def add_if_not_none(self, **kwargs: Any):
        for key, value in kwargs.items():
            if value is not None:
                self[key] = value


class TimberbornSize(dict):
    def __init__(self, X: int, Y: int):
        dict.__init__(self, X=X, Y=Y)


class TimberbornArray(dict):
    """ string-encoded array with a given delimeter """
    delimeter = " "

    def __init__(self, Array: List[object]):

        array_str = self.delimeter.join([str(x) for x in Array])
        dict.__init__(self, Array=array_str)

    @classmethod
    def load(Cls, Array: str, element_coerce: Any = int, delimeter: str = "", _validator=Validator(), raise_error=True):
        if not delimeter:
            delimeter = Cls.delimeter

        array_list = [element_coerce(i) for i in Array.split(Cls.delimeter)]
        return Cls(array_list)


class TimberbornMapSize(dict, LoadMixin):
    """ MapSize Singleton """
    load_args = [('Size', TimberbornSize)]

    def __init__(self, Size: TimberbornSize):
        dict.__init__(self, Size=Size)


class TimberbornTerrainMap(dict):
    """ TerrainMap Singleton """
    def __init__(self, Heights: TimberbornArray):
        dict.__init__(self, Heights=Heights)

    @classmethod
    def load(Cls, data: dict, _validator=Validator(), raise_error=True):
        return Cls(TimberbornArray.load(element_coerce=int, **data['Heights']))


class TimberbornSoilMoistureSimulator(dict):
    def __init__(self, MoistureLevels: TimberbornArray):
        dict.__init__(self, MoistureLevels=MoistureLevels)

    @classmethod
    def load(Cls, data: dict, _validator=Validator(), raise_error=True):
        return Cls(TimberbornArray.load(element_coerce=trunc_float, **data['MoistureLevels']))


class TimberbornWaterMap(dict):
    def __init__(self, WaterDepths: TimberbornArray, Outflows: TimberbornArray):
        dict.__init__(self, WaterDepths=WaterDepths, Outflows=Outflows)

    @classmethod
    def load(Cls, data: dict, _validator=Validator(), raise_error=True):
        obj = Cls(
            TimberbornArray.load(element_coerce=trunc_float, **data['WaterDepths']),
            TimberbornArray.load(element_coerce=str, **data['Outflows'])
        )
        return obj


class TimberbornSingletons(dict):
    def __init__(
        self,
        MapSize: TimberbornMapSize,
        SoilMoistureSimulator: TimberbornSoilMoistureSimulator,
        TerrainMap: TimberbornTerrainMap,
        WaterMap: TimberbornWaterMap,
    ):
        dict.__init__(
            self,
            MapSize=MapSize,
            SoilMoistureSimulator=SoilMoistureSimulator,
            TerrainMap=TerrainMap,
            WaterMap=WaterMap,
        )


class TimberbornEntity(dict):
    """ Enitity consists of Id, Template or TemplateName and Components """
    def __init__(self, TemplateName: str, Id: Optional[str] = None):
        if Id is None:
            Id = f"{uuid.uuid4()}"
        dict.__init__(self, Id=Id, TemplateName=TemplateName)

    @property
    def template(self):
        return self.get("TemplateName") or self.get("Template")

    @classmethod
    def load(Cls, data: dict, _validator=Validator(), raise_error=True):
        template = data.get('TemplateName') or data.get('Template')
        obj = Cls(Id=data['Id'], TemplateName=template)  # TODO replace TemplateName with Template ?
        return obj


class TimberbornCoordinates(LoadMixin, dict):
    load_args = (('X', int), ('Y', int), ('Z', int))

    def __init__(self, X: int, Y: int, Z: int):
        dict.__init__(self, X=X, Y=Y, Z=Z)


class TimberbornOrientation(LoadMixin, dict):
    """ Orientation for objects like buildings """
    load_args = [('Value', str)]  # TODO Rotation Validator

    def __init__(self, Value: str = "Cw0"):
        dict.__init__(self, Value=Value)


class TimberbornBlockObject(LoadMixin, dict):
    load_args = (('Coordinates', TimberbornCoordinates), ('Orientation', TimberbornOrientation))

    def __init__(self, Coordinates: TimberbornCoordinates, Orientation: Optional[TimberbornOrientation] = None):
        dict.__init__(self, Coordinates=Coordinates)
        if Orientation:
            self['Orientation'] = Orientation

    @classmethod
    def load(Cls, data: dict, _validator=Validator(), raise_error=True):
        print(data)
        return super().load(data, _validator)


class TimberbornGrowable(LoadMixin, dict):
    load_args = [("GrowthProgress", trunc_float2)]

    def __init__(self, GrowthProgress: float = 1.0):
        dict.__init__(self, GrowthProgress=GrowthProgress)


class TimberbornCoordinatesOffset(LoadMixin, dict):
    load_args = (('X', trunc_float), ('Y', trunc_float))

    def __init__(self, X: float, Y: float):
        dict.__init__(self, X=X, Y=Y)


class TimberbornCoordinatesOffseter(dict):
    def __init__(self, CoordinatesOffset: TimberbornCoordinatesOffset):
        dict.__init__(self, CoordinatesOffset=CoordinatesOffset)

    @classmethod
    def random(cls) -> "TimberbornCoordinatesOffseter":
        return cls(TimberbornCoordinatesOffset(pyrandom() * 0.25, pyrandom() * 0.25))

    # @classmethod
    # def load(Cls, data: dict):


class TimberbornNaturalResourceModelRandomizer(dict):
    def __init__(self, Rotation: float, DiameterScale: float, HeightScale: float, round_to: int = 6):
        if round_to:
            Rotation = round(Rotation, round_to)
            DiameterScale = round(DiameterScale, round_to)
            HeightScale = round(HeightScale, round_to)

        dict.__init__(self, Rotation=Rotation, DiameterScale=DiameterScale, HeightScale=HeightScale)

    @classmethod
    def random(cls) -> "TimberbornNaturalResourceModelRandomizer":
        scale = (pyrandom() * 0.75) + 0.5
        return TimberbornNaturalResourceModelRandomizer(pyrandom() * 360, scale, scale)


class TimberbornYielderCuttable(LoadMixin, dict):
    load_args = (('Yield', dict))

    def __init__(self, Id: str, Amount: int):
        dict.__init__(
            self,
            Yield={
                "Good": {
                    "Id": Id,
                },
                "Amount": Amount,
            },
        )

    @classmethod
    def load(Cls, Yield: dict, _validator: Validator = Validator(), raise_error=True):
        id = Yield['Yield']['Good']['Id']
        amount = Yield['Yield']['Amount']
        return Cls(id, amount)


# New Gatherable Objects
class TimberbornGatherableYieldGrower(dict):
    def __init__(self, GrowthProgress: float = -1.0, round_to: int = 2):
        if GrowthProgress < 0.0:
            GrowthProgress = pyrandom()
        if round_to:
            GrowthProgress = round(GrowthProgress, round_to)
        dict.__init__(self, GrowthProgress=GrowthProgress)


class TimberbornYielderGatherable(TimberbornYielderCuttable):
    pass


class TimberbornWateredObject(dict):
    def __init__(self, IsDry: bool):
        dict.__init__(self, IsDry=IsDry)


class TimberbornLivingNaturalResource(dict):
    def __init__(self, IsDead: bool):
        dict.__init__(self, IsDead=IsDead)


class TimberbornPrioritizable(dict):
    def __init__(self, Priority="Normal"):
        dict.__init__(self, Priority={"Value": Priority})


class TimberbornTreeComponents(LoadMixin, dict):
    load_args = (('BlockObject', TimberbornBlockObject),
                 ('CoordinatesOffseter', TimberbornCoordinatesOffseter),
                 ('Growable', TimberbornGrowable),
                 ('LivingNaturalResource', TimberbornLivingNaturalResource),
                 ('NaturalResourceModelRandomizer', TimberbornNaturalResourceModelRandomizer),
                 ('WateredObject', TimberbornWateredObject),
                 ('Yielder:Cuttable', TimberbornYielderCuttable),
                 ('GatherableYieldGrower', TimberbornGatherableYieldGrower),
                 ('Yielder:Gatherable', TimberbornYielderGatherable))

    def __init__(
        self,
        BlockObject: TimberbornBlockObject,
        CoordinatesOffseter: TimberbornCoordinatesOffseter,
        Growable: TimberbornGrowable,
        NaturalResourceModelRandomizer: TimberbornNaturalResourceModelRandomizer,
        YielderCuttable: TimberbornYielderCuttable,
        LivingNaturalResource: Optional[TimberbornLivingNaturalResource] = None,
        WateredObject: Optional[TimberbornWateredObject] = None,
        GatherableYieldGrower: Optional[TimberbornGatherableYieldGrower] = None,
        YielderGatherable: Optional[TimberbornYielderGatherable] = None,
    ):
        dict.__init__(
            self,
            BlockObject=BlockObject,
            BuilderJob={},
            CoordinatesOffseter=CoordinatesOffseter,
            Demolishable={},
            Growable=Growable,
            NaturalResourceModelRandomizer=NaturalResourceModelRandomizer,
            Prioritizable=TimberbornPrioritizable(),
        )
        self.add_if_not_none(
            LivingNaturalResource=LivingNaturalResource,
            WateredObject=WateredObject
        )

        self["Yielder:Cuttable"] = YielderCuttable
        self["Inventory:GoodStack"] = {"Storage": {"Goods": []}}
        if GatherableYieldGrower:
            if YielderGatherable:
                self["GatherableYieldGrower"] = GatherableYieldGrower
                self["Yielder:Gatherable"] = YielderGatherable
            else:
                logging.error("Components specified GatherableYieldGrower but not YielderGatherable,"
                              " may result game crashing on map validation.")


class TimberbornTree(TimberbornEntity):
    def __init__(self, species: str, Components: TimberbornTreeComponents):
        TimberbornEntity.__init__(self, species)
        self["Components"] = Components


class TimberbornMap(dict):
    def __init__(
        self,
        GameVersion: str,
        Singletons: TimberbornSingletons,
        Entities: List[TimberbornEntity],
    ):
        dict.__init__(self, GameVersion=GameVersion, Singletons=Singletons, Entities=Entities)
