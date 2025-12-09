(define (domain Welding-domain)
   (:requirements :typing)
   (:types
       location direction locatable property - object
       base_location weld_location - location
       hand agent - locatable
       h_type - property
   )

    (:predicates
       (at ?obj - locatable ?loc - location)
       (reachable ?loc_base - base_location ?loc_weld - weld_location)
       (hand_rel ?ag - locatable ?hg - locatable)
       (hand_type ?hg - hand ?htty - h_type)       (weld_type ?loc - weld_location ?htty - h_type)       (welded ?loc - weld_location)
       (not_welded ?loc - weld_location)
       (empty ?loc - location)
   )

   (:action move_hand
       :parameters (?ag - agent ?base_loc_from - base_location ?hg - hand ?weld_loc_from - weld_location ?weld_loc_to - weld_location)
       :precondition (and
           (at ?ag ?base_loc_from)
           (at ?hg ?weld_loc_from)
           (hand_rel ?ag ?hg)
           (reachable ?base_loc_from ?weld_loc_to)
           (empty ?weld_loc_to)
       )
       :effect (and
           (not (at ?hg ?weld_loc_from))
           (at ?hg ?weld_loc_to)
           (not (empty ?weld_loc_to))
           (empty ?weld_loc_from)
       )
   )

   (:action move_to_neutral
       :parameters (?ag - agent ?base_loc_from - base_location ?hg - hand ?weld_loc_from - weld_location)
       :precondition (and
           (at ?ag ?base_loc_from)
           (at ?hg ?weld_loc_from)
           (hand_rel ?ag ?hg)
       )
       :effect (and
           (not (at ?hg ?weld_loc_from))
           (at ?hg ?base_loc_from)
           (empty ?weld_loc_from)
       )
   )

   (:action move_from_neutral
       :parameters (?ag - agent ?base_loc_from - base_location ?hg - hand ?weld_loc_to - weld_location)
       :precondition (and
           (at ?ag ?base_loc_from)
           (at ?hg ?base_loc_from)
           (hand_rel ?ag ?hg)
           (reachable ?base_loc_from ?weld_loc_to)
           (empty ?weld_loc_to)
       )
       :effect (and
           (not (at ?hg ?base_loc_from))
           (at ?hg ?weld_loc_to)
           (not (empty ?weld_loc_to))
       )
   )

   (:action weld
       :parameters (?ag - agent ?base_loc_from - base_location ?hg - hand ?weld_loc_from - weld_location ?htty - h_type)
       :precondition (and
           (at ?ag ?base_loc_from)
           (at ?hg ?weld_loc_from)
           (hand_rel ?ag ?hg)
           (hand_type ?hg ?htty)
           (weld_type ?weld_loc_from ?htty)
           (not_welded ?weld_loc_from)
       )
       :effect (and
           (not (not_welded ?weld_loc_from))
           (welded ?weld_loc_from)
       )
   )

)